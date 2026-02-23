from decimal import Decimal
from typing import Dict

from addons.ads_manager.models import Campaign, CampaignMetric
from addons.ads_manager.tasks import sync_campaign_metrics


def compute_roi(campaign: Campaign) -> Dict[str, str]:
    metrics = campaign.metrics.all()
    total_spend = sum((m.spend for m in metrics), Decimal("0.00"))
    total_revenue = sum((m.revenue for m in metrics), Decimal("0.00"))
    roi = Decimal("0.00")
    if total_spend > 0:
        roi = ((total_revenue - total_spend) / total_spend) * Decimal("100")

    return {
        "campaign_id": campaign.id,
        "total_spend": str(total_spend),
        "total_revenue": str(total_revenue),
        "roi_percent": str(round(roi, 2)),
    }


def enforce_budget(campaign: Campaign) -> Dict[str, str]:
    latest = campaign.metrics.first()
    if latest and latest.spend > campaign.daily_budget:
        campaign.status = Campaign.Status.PAUSED
        campaign.save(update_fields=["status", "updated_at"])
        return {"status": "paused", "reason": "daily_budget_exceeded"}
    return {"status": campaign.status, "reason": "within_budget"}


def queue_metrics_sync(campaign: Campaign):
    sync_campaign_metrics.delay(campaign.id)
