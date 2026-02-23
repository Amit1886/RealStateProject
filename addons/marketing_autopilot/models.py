from django.db import models

from addons.common.models import AuditStampedModel, BranchScopedModel


class SocialAccountConnection(BranchScopedModel, AuditStampedModel):
    class Platform(models.TextChoices):
        FACEBOOK = "facebook", "Facebook"
        INSTAGRAM = "instagram", "Instagram"
        YOUTUBE = "youtube", "YouTube"
        LINKEDIN = "linkedin", "LinkedIn"
        X = "x", "X"

    platform = models.CharField(max_length=20, choices=Platform.choices)
    account_handle = models.CharField(max_length=120)
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("platform", "account_handle", "branch_code")


class ContentSchedule(BranchScopedModel, AuditStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SCHEDULED = "scheduled", "Scheduled"
        PUBLISHED = "published", "Published"
        FAILED = "failed", "Failed"

    platform = models.CharField(max_length=20, choices=SocialAccountConnection.Platform.choices)
    title = models.CharField(max_length=160)
    caption = models.TextField(blank=True)
    hashtags = models.CharField(max_length=500, blank=True)
    media_url = models.URLField(blank=True)
    scheduled_for = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    post_response = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-scheduled_for"]


class AutoReplyRule(BranchScopedModel, AuditStampedModel):
    platform = models.CharField(max_length=20, choices=SocialAccountConnection.Platform.choices)
    trigger_keyword = models.CharField(max_length=120)
    response_text = models.TextField()
    is_active = models.BooleanField(default=True)


class CreativeAsset(BranchScopedModel, AuditStampedModel):
    class AssetKind(models.TextChoices):
        BANNER = "banner", "Banner"
        POSTER = "poster", "Poster"
        REEL_SCRIPT = "reel_script", "Reel Script"
        VIDEO_EDIT = "video_edit", "Video Edit"

    kind = models.CharField(max_length=20, choices=AssetKind.choices)
    prompt = models.TextField()
    output_url = models.URLField(blank=True)
    status = models.CharField(max_length=20, default="queued")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
