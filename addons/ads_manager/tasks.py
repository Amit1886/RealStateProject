from decimal import Decimal

from celery import shared_task
from django.utils import timezone

from addons.ads_manager.models import Campaign, CampaignMetric


@shared_task
def sync_campaign_metrics(campaign_id: int):
    campaign = Campaign.objects.filter(id=campaign_id).first()
    if not campaign:
        return

    today = timezone.now().date()
    metric, _ = CampaignMetric.objects.get_or_create(campaign=campaign, metric_date=today)
    metric.impressions += 1000
    metric.clicks += 47
    metric.conversions += 3
    metric.spend += Decimal("250.00")
    metric.revenue += Decimal("820.00")
    metric.save()
