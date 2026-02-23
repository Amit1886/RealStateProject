from django.db.models.signals import post_save
from django.dispatch import receiver

from addons.ads_manager.models import Campaign
from addons.common.eventing import publish_event_safe


@receiver(post_save, sender=Campaign)
def campaign_events(sender, instance, created, **kwargs):
    publish_event_safe(
        event_key="ads_campaign_created" if created else "ads_campaign_updated",
        payload={
            "campaign_id": instance.id,
            "status": instance.status,
            "budget": str(instance.daily_budget),
            "platform": instance.account.platform,
        },
        branch_code=instance.branch_code,
        source="ads_manager",
    )
