from datetime import datetime
from typing import Dict

from addons.marketing_autopilot.models import ContentSchedule, CreativeAsset
from addons.marketing_autopilot.tasks import build_creative_asset, publish_scheduled_post


def generate_caption(topic: str, tone: str = "professional") -> str:
    return f"{topic} | Tone: {tone}. Discover how this helps your business today."


def generate_hashtags(topic: str) -> str:
    safe = "".join(ch for ch in topic.title() if ch.isalnum())
    return f"#{safe} #BusinessGrowth #Automation #SmartOps"


def schedule_post(payload: Dict) -> ContentSchedule:
    schedule = ContentSchedule.objects.create(
        branch_code=payload.get("branch_code", "default"),
        platform=payload["platform"],
        title=payload["title"],
        caption=payload.get("caption", ""),
        hashtags=payload.get("hashtags", ""),
        media_url=payload.get("media_url", ""),
        scheduled_for=payload["scheduled_for"],
        status=ContentSchedule.Status.SCHEDULED,
    )
    publish_scheduled_post.delay(schedule.id)
    return schedule


def queue_creative_asset(kind: str, prompt: str, branch_code: str = "default") -> CreativeAsset:
    asset = CreativeAsset.objects.create(branch_code=branch_code, kind=kind, prompt=prompt, status="queued")
    build_creative_asset.delay(asset.id)
    return asset
