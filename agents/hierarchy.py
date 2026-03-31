from __future__ import annotations

from decimal import Decimal

from agents.wallet import AgentWallet

DEFAULT_SUB_AGENT_COMMISSION = Decimal("0.70")  # 70% to sub-agent
DEFAULT_PARENT_COMMISSION = Decimal("0.30")    # 30% to parent
MLM_RULES = [Decimal("0.10"), Decimal("0.05"), Decimal("0.02")]  # level1, level2, level3
from agents.models import AgentRiskProfile


def ensure_wallet(agent):
    wallet, _ = AgentWallet.objects.get_or_create(agent=agent)
    return wallet


def distribute_commission(agent, amount: Decimal, *, source="lead_sale", note=""):
    """
    Splits commission between agent and upline up to 3 levels.
    """
    amount = Decimal(str(amount or 0))
    if amount <= 0:
        return
    current = agent
    level = 0
    remaining = amount
    while current and level < len(MLM_RULES):
        share_pct = MLM_RULES[level]
        share = (amount * share_pct).quantize(Decimal("0.01"))
        remaining -= share
        ensure_wallet(current).credit(share, source=f"{source}_L{level+1}", note=note)
        current = getattr(current, "parent_agent", None)
        level += 1

    # Remaining goes to origin agent
    credit_amount = max(remaining, Decimal("0.00"))
    wallet = ensure_wallet(agent)
    wallet.credit(credit_amount, source=source, note=note, lock=_should_lock(agent))


def _should_lock(agent):
    try:
        rp = agent.risk_profile
        return rp.risk_level == AgentRiskProfile.RiskLevel.HIGH
    except AgentRiskProfile.DoesNotExist:
        return False
