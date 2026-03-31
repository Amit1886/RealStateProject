from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from .models import UnitHold


@transaction.atomic
def release_hold(hold: UnitHold, *, reason: str = "") -> UnitHold:
    hold.status = UnitHold.HoldStatus.RELEASED
    hold.released_at = timezone.now()
    if reason:
        hold.reason = reason[:255]
    hold.save(update_fields=["status", "released_at", "reason", "payload"])
    return hold


def expire_due_holds():
    now = timezone.now()
    qs = UnitHold.objects.filter(status=UnitHold.HoldStatus.ACTIVE, hold_end__lt=now)
    updated = qs.update(status=UnitHold.HoldStatus.EXPIRED)
    return updated

