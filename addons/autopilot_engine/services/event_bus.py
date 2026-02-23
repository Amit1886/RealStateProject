from typing import Any, Dict, Optional

from django.conf import settings

from addons.common.services import safe_log
from addons.autopilot_engine.models import AutopilotEvent
from addons.autopilot_engine.tasks import process_autopilot_event


def publish_event(
    event_key: str,
    payload: Optional[Dict[str, Any]] = None,
    branch_code: str = "default",
    source: str = "system",
    actor=None,
    max_attempts: int = 3,
) -> AutopilotEvent:
    event = AutopilotEvent.objects.create(
        event_key=event_key,
        payload=payload or {},
        branch_code=branch_code,
        source=source,
        actor=actor,
        max_attempts=max_attempts,
    )

    safe_log("published", {"event_id": event.id, "event_key": event_key})

    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
        process_autopilot_event(event.id)
    else:
        process_autopilot_event.delay(event.id)
    return event
