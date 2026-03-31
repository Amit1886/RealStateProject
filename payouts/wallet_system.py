from decimal import Decimal

from agents.hierarchy import distribute_commission


def credit_on_lead_close(lead):
    """
    Credits agent wallet when a lead is closed with a deal_value.
    """
    if not getattr(lead, "assigned_agent", None):
        return
    amount = Decimal(str(getattr(lead, "deal_value", 0) or 0))
    if amount <= 0:
        return
    commission = amount * Decimal("0.02")
    distribute_commission(lead.assigned_agent, commission, source="lead_close", note=f"Lead {lead.id}")
