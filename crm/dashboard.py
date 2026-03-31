from datetime import timedelta

from django.db import models
from django.utils import timezone

from leads.models import Lead
from visits.models import SiteVisit
from deals.models import Deal
from agents.models import Agent


def admin_super_dashboard(filters: dict | None = None) -> dict:
    filters = filters or {}
    qs = Lead.objects.all()
    if city := filters.get("city"):
        qs = qs.filter(assigned_agent__city__iexact=city)
    if agent_id := filters.get("agent"):
        qs = qs.filter(assigned_agent_id=agent_id)
    if source := filters.get("source"):
        qs = qs.filter(source=source)
    if since := filters.get("since"):
        qs = qs.filter(created_at__gte=since)

    closed_qs = qs.filter(status=Lead.Status.CLOSED)
    visits_qs = SiteVisit.objects.all()
    deals_qs = Deal.objects.all()

    data = {
        "live_leads": qs.filter(created_at__gte=timezone.now() - timedelta(hours=1)).count(),
        "funnel": list(qs.values("stage").annotate(count=models.Count("id")).order_by()),
        "revenue": closed_qs.aggregate(total=models.Sum("deal_value"))["total"] or 0,
        "agent_leaderboard": list(
            closed_qs.values("assigned_agent", "assigned_agent__name").annotate(
                closed=models.Count("id"), revenue=models.Sum("deal_value")
            ).order_by("-revenue")[:10]
        ),
        "conversion_rate": _conv_rate(qs),
        "visits": visits_qs.count(),
        "deals": deals_qs.count(),
        "active_agents": Agent.objects.filter(is_active=True).count(),
    }
    return data


def _conv_rate(qs):
    total = qs.count()
    if total == 0:
        return 0
    closed = qs.filter(status=Lead.Status.CLOSED).count()
    return round((closed / total) * 100, 2)
