from django.db import models

from addons.common.models import AuditStampedModel, BranchScopedModel


class CallSession(BranchScopedModel, AuditStampedModel):
    class Status(models.TextChoices):
        NEW = "new", "New"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    caller_number = models.CharField(max_length=20, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW, db_index=True)
    language = models.CharField(max_length=20, default="hi")
    detected_intent = models.CharField(max_length=80, blank=True)
    transcript = models.TextField(blank=True)
    linked_order_ref = models.CharField(max_length=80, blank=True)
    crm_synced = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]


class CallLog(models.Model):
    session = models.ForeignKey(CallSession, on_delete=models.CASCADE, related_name="logs")
    event_type = models.CharField(max_length=80)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class WhatsAppFollowUp(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    session = models.ForeignKey(CallSession, on_delete=models.CASCADE, related_name="whatsapp_followups")
    message = models.TextField()
    scheduled_for = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    provider_message_id = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class WhatsAppProviderConfig(BranchScopedModel, AuditStampedModel):
    class Provider(models.TextChoices):
        META_CLOUD = "meta_cloud", "Meta WhatsApp Cloud"
        TWILIO = "twilio", "Twilio"
        OTHER = "other", "Other"

    provider = models.CharField(max_length=40, choices=Provider.choices, default=Provider.META_CLOUD)
    is_active = models.BooleanField(default=True, db_index=True)
    sandbox = models.BooleanField(default=True)
    demo_sender = models.CharField(max_length=40, blank=True)  # phone number id / sender id
    access_token = models.TextField(blank=True)
    webhook_verify_token = models.CharField(max_length=120, blank=True)
    extra = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("branch_code", "provider")
        ordering = ["branch_code", "provider"]


class IVRProviderConfig(BranchScopedModel, AuditStampedModel):
    class Provider(models.TextChoices):
        EXOTEL = "exotel", "Exotel"
        TWILIO = "twilio", "Twilio"
        OTHER = "other", "Other"

    provider = models.CharField(max_length=40, choices=Provider.choices, default=Provider.EXOTEL)
    is_active = models.BooleanField(default=True, db_index=True)
    sandbox = models.BooleanField(default=True)
    demo_number = models.CharField(max_length=40, blank=True)
    api_key = models.CharField(max_length=200, blank=True)
    api_secret = models.CharField(max_length=200, blank=True)
    extra = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("branch_code", "provider")
        ordering = ["branch_code", "provider"]
