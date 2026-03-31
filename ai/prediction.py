from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from leads.models import Lead


def predict_conversion_probability(lead: Lead) -> float:
    """
    Lightweight heuristic prediction using existing score and freshness.
    """
    base = lead.lead_score or 0
    age_days = (timezone.now() - lead.created_at).days
    age_penalty = max(0, age_days - 7) * 1.5
    budget_bonus = float(Decimal(str(lead.budget or 0)) / Decimal("1000000"))
    prob = max(5.0, min(95.0, base - age_penalty + budget_bonus))
    return round(prob, 2)


def predict_expected_revenue(agent=None, days_ahead=30):
    qs = Lead.objects.filter(status=Lead.Status.CLOSED)
    if agent:
        qs = qs.filter(assigned_agent=agent)
    avg = qs.aggregate_avg = qs.aggregate(val=("deal_value")) if hasattr(qs, "aggregate_avg") else None
    avg_val = avg["val"] if isinstance(avg, dict) else 0
    return avg_val
