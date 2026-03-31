from __future__ import annotations

from celery import shared_task
from django.utils import timezone

from marketing.models import Campaign
from marketing.services import start_campaign


@shared_task
def process_scheduled_campaigns():
    now = timezone.now()
    qs = Campaign.objects.filter(status=Campaign.Status.SCHEDULED, scheduled_at__lte=now).order_by("scheduled_at")[:50]
    for campaign in qs:
        try:
            start_campaign(campaign=campaign, actor=campaign.created_by)
        except Exception as exc:
            campaign.mark_failed(str(exc))

