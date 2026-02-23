from __future__ import annotations

import logging
import os
from typing import Any, Dict

from django.conf import settings
from django.db.utils import OperationalError, ProgrammingError
from django.dispatch import receiver

from addons.common.eventing import addon_event_published
from addons.common.services import safe_log

logger = logging.getLogger(__name__)


def _env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return str(val).strip().lower() in {"1", "true", "yes", "y", "on"}


def _autopilot_enabled() -> bool:
    if not _env_bool("ADDONS_PLATFORM_ENABLED", False):
        return False

    if _env_bool("ADDON_AUTOPILOT_ENGINE_ENABLED", False):
        return True

    # If not explicitly enabled via env, fall back to DB toggle when available.
    try:
        from addons.autopilot_engine.models import FeatureToggle

        return bool(FeatureToggle.objects.filter(key="autopilot_engine", enabled=True).first())
    except (OperationalError, ProgrammingError):
        return False


@receiver(addon_event_published)
def persist_and_dispatch_addon_event(
    sender: Any,
    *,
    event_key: str,
    payload: Dict,
    branch_code: str,
    source: str,
    actor=None,
    max_attempts: int = 3,
    **kwargs,
) -> None:
    if not _autopilot_enabled():
        return

    try:
        from addons.autopilot_engine.models import AutopilotEvent
        from addons.autopilot_engine.tasks import process_autopilot_event

        event = AutopilotEvent.objects.create(
            event_key=event_key,
            payload=payload or {},
            branch_code=branch_code or "default",
            source=source or "system",
            actor=actor,
            max_attempts=max_attempts,
        )
        safe_log("autopilot_event_persisted", {"event_id": event.id, "event_key": event_key, "source": source})

        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            process_autopilot_event(event.id)
        else:
            process_autopilot_event.delay(event.id)
    except (OperationalError, ProgrammingError):
        # DB/migrations not ready: never block core workflows.
        logger.warning("autopilot_engine not ready (missing tables); skipping event persist", exc_info=True)
    except Exception:  # pragma: no cover
        logger.exception("autopilot_engine failed to persist/dispatch event")

