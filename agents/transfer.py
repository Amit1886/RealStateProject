from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from deals.models import Deal
from leads.models import Lead

from .models import Agent, AgentTransfer


@transaction.atomic
def perform_agent_transfer(*, old_agent: Agent, new_agent: Agent, transferred_by=None, transfer_type: str = "both", reason: str = "") -> AgentTransfer:
    now = timezone.now()
    lead_count = 0
    deal_count = 0
    lead_ids = list(Lead.objects.filter(assigned_agent=old_agent).values_list("id", flat=True))
    deal_ids = list(Deal.objects.filter(agent=old_agent).values_list("id", flat=True))

    if transfer_type in {"leads", "both"}:
        lead_count = Lead.objects.filter(assigned_agent=old_agent).update(
            assigned_agent=new_agent,
            assigned_to=new_agent.user,
            last_reassigned_at=now,
            updated_at=now,
        )

    if transfer_type in {"deals", "both"}:
        deal_count = Deal.objects.filter(agent=old_agent).update(agent=new_agent)

    transfer = AgentTransfer.objects.create(
        old_agent=old_agent,
        new_agent=new_agent,
        transferred_by=transferred_by,
        transfer_type=transfer_type,
        reason=(reason or "")[:255],
        reassigned_leads=lead_count,
        reassigned_deals=deal_count,
        payload={
            "old_agent_id": old_agent.id,
            "new_agent_id": new_agent.id,
            "lead_ids": lead_ids[:500],
            "deal_ids": deal_ids[:500],
        },
    )
    return transfer
