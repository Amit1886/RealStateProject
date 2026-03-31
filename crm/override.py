from __future__ import annotations

from django.db import transaction

from .models import OverrideLog


@transaction.atomic
def log_override(*, admin=None, action_type: str, target_model: str, target_object_id: str = "", old_value=None, new_value=None, reason: str = ""):
    return OverrideLog.objects.create(
        admin=admin,
        action_type=action_type,
        target_model=target_model,
        target_object_id=str(target_object_id or ""),
        old_value=old_value or {},
        new_value=new_value or {},
        reason=(reason or "")[:255],
    )

