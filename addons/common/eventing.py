from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from django.dispatch import Signal

from .services import safe_log

logger = logging.getLogger(__name__)


addon_event_published = Signal()


def publish_event(
    *,
    event_key: str,
    payload: Optional[Dict[str, Any]] = None,
    branch_code: str = "default",
    source: str = "system",
    actor: Any = None,
    max_attempts: int = 3,
) -> None:
    safe_log("addon_event_published", {"event_key": event_key, "source": source, "branch_code": branch_code})
    addon_event_published.send(
        sender=None,
        event_key=event_key,
        payload=payload or {},
        branch_code=branch_code,
        source=source,
        actor=actor,
        max_attempts=max_attempts,
    )


def publish_event_safe(**kwargs: Any) -> None:
    try:
        publish_event(**kwargs)
    except Exception:  # pragma: no cover
        logger.exception("addon publish_event failed", extra={"kwargs": kwargs})
