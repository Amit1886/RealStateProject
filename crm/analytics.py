from datetime import timedelta

from django.db import models
from django.utils import timezone

from leads.models import Lead
from deals.models import Deal
from visits.models import SiteVisit


def funnel_analytics(days=30):
    since = timezone.now() - timedelta(days=days)
    qs = Lead.objects.filter(created_at__gte=since)
    return {
        "funnel": list(qs.values("stage").annotate(count=models.Count("id")).order_by()),
        "source_mix": list(qs.values("source").annotate(count=models.Count("id")).order_by()),
        "avg_score": qs.aggregate(avg=models.Avg("lead_score"))["avg"] or 0,
    }


def visit_conversion():
    visits = SiteVisit.objects.count()
    closed_after_visit = Lead.objects.filter(stage=Lead.Stage.CLOSED, site_visits__isnull=False).distinct().count()
    return {"visits": visits, "closed_after_visit": closed_after_visit}


def revenue_trend(days=90):
    since = timezone.now() - timedelta(days=days)
    qs = Deal.objects.filter(created_at__gte=since, status=Deal.Status.WON)
    return list(qs.extra({"day": "date(created_at)"}).values("day").annotate(total=models.Sum("deal_amount")).order_by("day"))
