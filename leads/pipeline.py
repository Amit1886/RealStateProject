from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from leads.models import Lead


STAGE_MAX_DURATIONS = {
    Lead.Stage.NEW: timedelta(days=1),
    Lead.Stage.QUALIFIED: timedelta(days=2),
    Lead.Stage.VISIT: timedelta(days=3),
    Lead.Stage.NEGOTIATION: timedelta(days=3),
}


def refresh_stage_deadline(lead: Lead, *, stage_changed_at=None):
    stage_changed_at = stage_changed_at or timezone.now()
    lead.stage_updated_at = stage_changed_at
    lead.stage_deadline = (
        stage_changed_at + STAGE_MAX_DURATIONS.get(lead.stage, timedelta(0))
        if lead.stage in STAGE_MAX_DURATIONS
        else None
    )
    lead.is_overdue = False
    lead.save(update_fields=["stage_updated_at", "stage_deadline", "is_overdue", "updated_at"])
    return lead


def check_deadline_breach():
    now = timezone.now()
    breached = []
    qs = Lead.objects.filter(stage_deadline__isnull=False, stage_deadline__lt=now, is_overdue=False).exclude(
        stage__in=[Lead.Stage.CONVERTED, Lead.Stage.CLOSED, Lead.Stage.DEAL_CLOSED, Lead.Stage.LOST_LEAD]
    )
    for lead in qs.iterator():
        lead.is_overdue = True
        lead.save(update_fields=["is_overdue", "updated_at"])
        breached.append(lead.id)
    return breached


def record_visit_no_show(lead: Lead, *, penalty: int = 10):
    lead.no_show_count = (lead.no_show_count or 0) + 1
    lead.reliability_score = max(0, int(lead.reliability_score or 0) - max(0, int(penalty or 0)))
    lead.save(update_fields=["no_show_count", "reliability_score", "updated_at"])
    return lead


def calculate_closing_ratio(agent):
    total_leads = Lead.objects.filter(assigned_agent=agent).count()
    closed_leads = Lead.objects.filter(
        assigned_agent=agent, status__in=[Lead.Status.CLOSED, Lead.Status.CONVERTED, Lead.Status.WON]
    ).count()
    ratio = Decimal(str((closed_leads / total_leads * 100) if total_leads else 0)).quantize(Decimal("0.01"))
    snapshot = None
    try:
        from agents.models import AgentPerformanceSnapshot

        snapshot, _ = AgentPerformanceSnapshot.objects.update_or_create(
            agent=agent,
            date=timezone.localdate(),
            defaults={
                "total_leads": total_leads,
                "closed_leads": closed_leads,
                "closing_ratio": ratio,
            },
        )
    except Exception:
        snapshot = None
    return {
        "total_leads": total_leads,
        "closed_leads": closed_leads,
        "closing_ratio": ratio,
        "snapshot": snapshot,
    }


def move_stage(lead: Lead, new_stage: str, *, actor=None, note: str = ""):
    """
    Update stage and cascade status where relevant.
    """
    if new_stage not in dict(Lead.Stage.choices):
        return lead
    lead.stage = new_stage
    lead.stage_updated_at = timezone.now()
    lead.stage_deadline = (
        lead.stage_updated_at + STAGE_MAX_DURATIONS.get(new_stage, timedelta(0))
        if new_stage in STAGE_MAX_DURATIONS
        else None
    )
    lead.is_overdue = False
    if new_stage in {
        Lead.Stage.CONTACTED,
        Lead.Stage.FOLLOW_UP,
        Lead.Stage.INTERESTED,
        Lead.Stage.VISIT,
        Lead.Stage.SITE_VISIT,
        Lead.Stage.VISIT_SCHEDULED,
        Lead.Stage.NEGOTIATION,
    } and lead.status == Lead.Status.NEW:
        lead.status = Lead.Status.IN_PROGRESS
    if new_stage == Lead.Stage.CONVERTED:
        lead.status = Lead.Status.CONVERTED
    if new_stage in {Lead.Stage.CLOSED, Lead.Stage.DEAL_CLOSED}:
        lead.status = Lead.Status.CLOSED
    if new_stage == Lead.Stage.LOST_LEAD:
        lead.status = Lead.Status.LOST
    lead.save(update_fields=["stage", "status", "stage_updated_at", "stage_deadline", "is_overdue", "updated_at"])
    if note:
        from leads.models import LeadActivity

        LeadActivity.objects.create(lead=lead, actor=actor, activity_type="stage_change", note=note[:300])
    return lead
