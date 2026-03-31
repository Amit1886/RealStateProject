from decimal import Decimal
from django.db import transaction
from deals.models_commission import Commission
from wallet.models import Wallet, WalletTransaction


def settle_commission(commission: Commission):
    """
    Atomically credit admin/agent/sub-agent wallets based on commission breakdown.
    """
    if commission.settled:
        return commission

    with transaction.atomic():
        _credit_wallet(commission.deal.agent.user, commission.agent_amount, "commission:agent")
        if commission.sub_agent_amount > 0 and getattr(commission.deal.agent, "parent_agent", None):
            parent_user = commission.deal.agent.parent_agent.user
            _credit_wallet(parent_user, commission.sub_agent_amount, "commission:sub-agent")
        # Admin credit routed to company owner (first admin user of company); fallback to superuser.
        admin_user = _pick_admin_user(commission)
        if admin_user:
            _credit_wallet(admin_user, commission.admin_amount, "commission:admin")
        commission.settled = True
        commission.save(update_fields=["settled"])
    return commission


def _credit_wallet(user, amount: Decimal, source: str):
    wallet, _ = Wallet.objects.select_for_update().get_or_create(user=user)
    wallet.balance = (wallet.balance or Decimal("0.00")) + amount
    wallet.save(update_fields=["balance", "updated_at"])
    WalletTransaction.objects.create(
        wallet=wallet,
        entry_type=WalletTransaction.EntryType.CREDIT,
        amount=amount,
        source=source,
        reference="",
        metadata={},
    )


def _pick_admin_user(commission: Commission):
    company = getattr(commission, "company", None) or getattr(commission.deal, "company", None)
    if not company:
        return None
    user = company.users.filter(is_staff=True, is_active=True).order_by("id").first()
    if user:
        return user
    from django.contrib.auth import get_user_model

    return get_user_model().objects.filter(is_superuser=True).first()
