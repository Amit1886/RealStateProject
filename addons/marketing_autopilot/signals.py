from django.db.models.signals import post_save
from django.dispatch import receiver

from addons.common.eventing import publish_event_safe
from addons.marketing_autopilot.models import ContentSchedule


@receiver(post_save, sender=ContentSchedule)
def marketing_schedule_events(sender, instance, created, **kwargs):
    event_key = "marketing_schedule_created" if created else "marketing_schedule_updated"
    publish_event_safe(
        event_key=event_key,
        payload={
            "schedule_id": instance.id,
            "platform": instance.platform,
            "status": instance.status,
        },
        branch_code=instance.branch_code,
        source="marketing_autopilot",
    )
