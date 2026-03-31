from __future__ import annotations

from celery import shared_task

from leads.models import Lead
from leads.services import (
    auto_assign_lead,
    process_due_followups,
    reassign_stale_leads,
    refresh_lead_score,
    send_inactive_lead_followups,
)


@shared_task
def auto_assign_lead_task(lead_id: int):
    lead = Lead.objects.filter(id=lead_id).first()
    if not lead:
        return False
    auto_assign_lead(lead=lead)
    return True


@shared_task
def process_due_followups_task():
    process_due_followups()
    return True


@shared_task
def reassign_stale_leads_task():
    return reassign_stale_leads()


@shared_task
def send_inactive_lead_followups_task():
    return send_inactive_lead_followups()


@shared_task
def refresh_open_lead_scores_task():
    qs = Lead.objects.exclude(status__in=[Lead.Status.CLOSED, Lead.Status.LOST]).order_by("-updated_at")[:500]
    refreshed = 0
    for lead in qs:
        refresh_lead_score(lead)
        refreshed += 1
    return refreshed
