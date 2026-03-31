from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from agents.hierarchy import ensure_wallet
from crm.override import log_override
from .models_commission import Commission


@transaction.atomic
def adjust_payment(payment, *, adjusted_amount, note: str = "", actor=None):
    previous = {
        "amount": str(payment.amount),
        "adjusted_amount": str(payment.adjusted_amount),
        "adjustment_note": payment.adjustment_note,
    }
    payment.adjusted_amount = adjusted_amount
    payment.adjustment_note = (note or "")[:255]
    history = list(payment.adjustment_history or [])
    history.append(
        {
            "timestamp": timezone.now().isoformat(),
            "actor_id": getattr(actor, "id", None),
            "previous": previous,
            "new": {"adjusted_amount": str(adjusted_amount), "adjustment_note": payment.adjustment_note},
        }
    )
    payment.adjustment_history = history
    payment.save(update_fields=["adjusted_amount", "adjustment_note", "adjustment_history", "updated_at"])
    log_override(
        admin=actor if getattr(actor, "is_staff", False) else None,
        action_type="payment_adjustment",
        target_model="deals.Payment",
        target_object_id=str(payment.pk),
        old_value=previous,
        new_value={"adjusted_amount": str(adjusted_amount), "adjustment_note": payment.adjustment_note},
        reason=payment.adjustment_note or note or "Payment adjusted",
    )
    return payment


@transaction.atomic
def settle_deal_commission(
    deal,
    *,
    actor=None,
    settled: bool = False,
    credit_agent_wallet: bool = False,
    payment_invoice_number: str = "",
    note: str = "",
):
    commission, _ = Commission.objects.select_for_update().get_or_create(
        deal=deal,
        defaults={
            "company": deal.company,
            "admin_amount": (deal.commission_amount * deal.company_share_percent) / Decimal("100.00"),
            "agent_amount": (deal.commission_amount * deal.agent_share_percent) / Decimal("100.00"),
            "sub_agent_amount": Decimal("0.00"),
            "total_amount": deal.commission_amount,
            "settled": False,
        },
    )
    updates = []
    if commission.company_id != deal.company_id:
        commission.company = deal.company
        updates.append("company")
    if commission.total_amount != deal.commission_amount:
        commission.total_amount = deal.commission_amount
        updates.append("total_amount")
    expected_admin_amount = (deal.commission_amount * deal.company_share_percent) / Decimal("100.00")
    expected_agent_amount = (deal.commission_amount * deal.agent_share_percent) / Decimal("100.00")
    if commission.admin_amount != expected_admin_amount:
        commission.admin_amount = expected_admin_amount
        updates.append("admin_amount")
    if commission.agent_amount != expected_agent_amount:
        commission.agent_amount = expected_agent_amount
        updates.append("agent_amount")
    if settled and not commission.settled:
        commission.settled = True
        updates.append("settled")

    meta = dict(commission.metadata or {})
    if payment_invoice_number:
        meta["payment_invoice"] = payment_invoice_number
    if settled:
        meta["settled_by"] = getattr(actor, "id", None)
        meta["settled_at"] = timezone.now().isoformat()
    if credit_agent_wallet and not meta.get("wallet_credited"):
        payout_amount = commission.agent_amount or commission.total_amount or deal.commission_amount
        if payout_amount > 0 and deal.agent_id:
            wallet = ensure_wallet(deal.agent)
            wallet.credit(
                payout_amount,
                source="commission_release",
                note=note or f"Commission release for deal {deal.id}",
            )
            meta["wallet_credited"] = True
            meta["wallet_credit_amount"] = str(payout_amount)
            meta["wallet_credited_at"] = timezone.now().isoformat()
            meta["wallet_credited_by"] = getattr(actor, "id", None)
    if note:
        meta["release_note"] = note
    commission.metadata = meta
    updates.append("metadata")
    commission.save(update_fields=list(dict.fromkeys(updates)) + ["updated_at"])
    return commission
