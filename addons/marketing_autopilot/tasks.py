from celery import shared_task
from django.utils import timezone

from addons.marketing_autopilot.models import ContentSchedule, CreativeAsset


@shared_task
def publish_scheduled_post(schedule_id: int):
    schedule = ContentSchedule.objects.filter(id=schedule_id).first()
    if not schedule:
        return
    if schedule.scheduled_for > timezone.now():
        return

    schedule.status = ContentSchedule.Status.PUBLISHED
    schedule.post_response = {"external_id": f"post-{schedule.id}", "status": "published"}
    schedule.save(update_fields=["status", "post_response", "updated_at"])


@shared_task
def build_creative_asset(asset_id: int):
    asset = CreativeAsset.objects.filter(id=asset_id).first()
    if not asset:
        return
    asset.status = "ready"
    asset.output_url = f"https://assets.local/{asset.kind}/{asset.id}.mp4"
    asset.metadata = {"generator": "placeholder", "quality": "standard"}
    asset.save(update_fields=["status", "output_url", "metadata", "updated_at"])
