import logging
from typing import Dict

from django.db import transaction
from django.utils import timezone

from addons.autopilot_engine.models import (
    AutopilotEvent,
    AutopilotExecution,
    AutopilotStepLog,
    WorkflowRule,
)
from addons.autopilot_engine.services.actions import ActionExecutionError, registry
from addons.autopilot_engine.services.rules import rule_matches

logger = logging.getLogger(__name__)


class RetryableEventError(Exception):
    pass


def _log_step(execution: AutopilotExecution, action_key: str, status: str, response: Dict, error: str = "", attempt: int = 1):
    AutopilotStepLog.objects.create(
        execution=execution,
        action_key=action_key,
        status=status,
        response=response,
        error=error,
        attempt=attempt,
    )


def execute_event(event_id: int):
    with transaction.atomic():
        event = AutopilotEvent.objects.select_for_update().get(id=event_id)

        if event.status == AutopilotEvent.Status.SUCCESS:
            return

        event.status = AutopilotEvent.Status.RUNNING
        event.attempts += 1
        event.save(update_fields=["status", "attempts", "updated_at"])

        rules = WorkflowRule.objects.filter(
            event_key=event.event_key,
            is_active=True,
            branch_code=event.branch_code,
        ).prefetch_related("actions")

        if not rules.exists():
            event.status = AutopilotEvent.Status.SUCCESS
            event.save(update_fields=["status", "updated_at"])
            return

        event_failed = False
        first_error = ""

        for rule in rules:
            match, reason = rule_matches(rule.conditions, event.payload, event.branch_code)
            execution = AutopilotExecution.objects.create(event=event, rule=rule)

            if not match:
                _log_step(
                    execution,
                    action_key="rule_gate",
                    status=AutopilotStepLog.Status.SKIPPED,
                    response={"reason": reason},
                )
                execution.status = AutopilotExecution.Status.SUCCESS
                execution.save(update_fields=["status", "updated_at"])
                continue

            context = {"event": event, "rule": rule}
            execution_failed = False

            for action in rule.actions.all():
                attempt = 1
                while attempt <= max(1, action.retry_limit):
                    try:
                        with transaction.atomic():
                            sid = transaction.savepoint()
                            response = registry.execute(action.action_key, context=context, params=action.params)
                            _log_step(
                                execution,
                                action_key=action.action_key,
                                status=AutopilotStepLog.Status.SUCCESS,
                                response=response,
                                attempt=attempt,
                            )
                            transaction.savepoint_commit(sid)
                        break
                    except ActionExecutionError as exc:
                        msg = str(exc)
                        _log_step(
                            execution,
                            action_key=action.action_key,
                            status=AutopilotStepLog.Status.FAILED,
                            response={},
                            error=msg,
                            attempt=attempt,
                        )
                        execution_failed = True
                        if not first_error:
                            first_error = msg
                        if action.critical:
                            break
                    except Exception as exc:  # pragma: no cover
                        msg = f"unexpected:{exc}"
                        logger.exception("autopilot action crash")
                        _log_step(
                            execution,
                            action_key=action.action_key,
                            status=AutopilotStepLog.Status.FAILED,
                            response={},
                            error=msg,
                            attempt=attempt,
                        )
                        execution_failed = True
                        if not first_error:
                            first_error = msg
                        if action.critical:
                            break
                    attempt += 1

                if execution_failed and action.critical:
                    break

            if execution_failed:
                execution.status = AutopilotExecution.Status.FAILED
                execution.failure_reason = first_error or "action_failed"
                event_failed = True
            else:
                execution.status = AutopilotExecution.Status.SUCCESS
            execution.save(update_fields=["status", "failure_reason", "updated_at"])

        if event_failed:
            if event.attempts < event.max_attempts:
                event.status = AutopilotEvent.Status.RETRY
                event.last_error = first_error
                event.save(update_fields=["status", "last_error", "updated_at"])
                raise RetryableEventError(first_error or "retry_requested")

            event.status = AutopilotEvent.Status.FAILED
            event.last_error = first_error or "max_attempts_reached"
            event.save(update_fields=["status", "last_error", "updated_at"])
            return

        event.status = AutopilotEvent.Status.SUCCESS
        event.last_error = ""
        event.save(update_fields=["status", "last_error", "updated_at"])
