from decimal import Decimal

# existing imports remain; file already exists, we extend via helper

from django.conf import settings

from payouts.models import Payout
from agents.wallet import AgentWallet
from decimal import Decimal
from typing import Optional


def create_payout_with_lock(agent, lead, amount: Decimal, generated_by=None):
    """
    Creates a payout and locks the wallet balance until approved.
    """
    wallet, _ = AgentWallet.objects.get_or_create(agent=agent)
    wallet.credit(amount, source="payout_lock", note=f"Lead {getattr(lead, 'id', '')}", lock=True)
    return Payout.objects.create(
        agent=agent,
        lead=lead,
        amount=amount,
        status=Payout.Status.PENDING,
        generated_by=generated_by,
        metadata={"lock": True},
    )


def create_payout_for_lead(lead, generated_by=None, amount: Optional[Decimal] = None):
    """
    Backward-compatible helper used across the app.
    """
    if not getattr(lead, "assigned_agent", None):
        return None
    amount = Decimal(str(amount or getattr(lead, "deal_value", 0) or 0))
    if amount <= 0:
        rate = Decimal(str(getattr(settings, "AGENT_PAYOUT_RATE", "0.10")))
        amount = Decimal(str(getattr(lead, "deal_value", 0) or 0)) * rate
    payout, _ = Payout.objects.get_or_create(
        lead=lead,
        agent=lead.assigned_agent,
        defaults={
            "amount": amount,
            "currency": getattr(settings, "DEFAULT_CURRENCY", "INR"),
            "generated_by": generated_by,
            "status": Payout.Status.PENDING,
        },
    )
    return payout
