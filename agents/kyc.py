from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from .models import Agent, AgentVerification


@transaction.atomic
def approve_agent_kyc(agent: Agent, *, admin=None, document=None, remarks: str = "") -> Agent:
    if document is not None:
        agent.kyc_document = document
    agent.kyc_status = "verified"
    agent.kyc_verified_at = timezone.now()
    agent.save(update_fields=["kyc_document", "kyc_status", "kyc_verified_at", "updated_at"])
    AgentVerification.objects.filter(agent=agent).update(
        status=AgentVerification.Status.APPROVED,
        verified_by=admin,
        reviewed_at=timezone.now(),
        remarks=(remarks or "")[:255],
    )
    return agent


@transaction.atomic
def reject_agent_kyc(agent: Agent, *, admin=None, remarks: str = "") -> Agent:
    agent.kyc_status = "rejected"
    agent.save(update_fields=["kyc_status", "updated_at"])
    AgentVerification.objects.filter(agent=agent).update(
        status=AgentVerification.Status.REJECTED,
        verified_by=admin,
        reviewed_at=timezone.now(),
        remarks=(remarks or "")[:255],
    )
    return agent
