from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


class Campaign(models.Model):
    class Channel(models.TextChoices):
        WHATSAPP = "whatsapp", "WhatsApp"
        SMS = "sms", "SMS"
        EMAIL = "email", "Email"
        FACEBOOK = "facebook", "Facebook Ads"
        INSTAGRAM = "instagram", "Instagram Ads"
        GOOGLE = "google", "Google Ads"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SCHEDULED = "scheduled", "Scheduled"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    company = models.ForeignKey(
        "core_settings.CompanySettings",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="campaigns",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campaigns_created",
    )
    channel = models.CharField(max_length=20, choices=Channel.choices, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)

    name = models.CharField(max_length=140)
    audience = models.JSONField(default=dict, blank=True, help_text="Filter definition for audience selection.")
    ai_prompt = models.TextField(blank=True, default="")
    ad_copy = models.TextField(blank=True, default="")
    ai_creative_url = models.URLField(blank=True, default="")
    language = models.CharField(max_length=16, default="auto", help_text="auto / hi / en / hi-en")
    pincodes = models.JSONField(default=list, blank=True, help_text="Hyperlocal targeting (list of pincodes)")
    budget_daily = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    budget_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    optimize_goal = models.CharField(max_length=40, blank=True, default="", help_text="cpa / ctr / conversions")
    metadata = models.JSONField(default=dict, blank=True)

    scheduled_at = models.DateTimeField(null=True, blank=True, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, default="")

    recipients_total = models.PositiveIntegerField(default=0)
    recipients_sent = models.PositiveIntegerField(default=0)
    recipients_failed = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["company", "status", "scheduled_at"])]

    def mark_running(self):
        if self.status != self.Status.RUNNING:
            self.status = self.Status.RUNNING
            self.started_at = timezone.now()
            self.save(update_fields=["status", "started_at", "updated_at"])

    def mark_completed(self):
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at", "updated_at"])

    def mark_failed(self, error: str):
        self.status = self.Status.FAILED
        self.last_error = (error or "")[:2000]
        self.save(update_fields=["status", "last_error", "updated_at"])

    def __str__(self) -> str:
        return f"{self.name} ({self.channel})"


class QRCode(models.Model):
    class Kind(models.TextChoices):
        AGENT = "agent", "Agent QR"
        CAMPAIGN = "campaign", "Campaign QR"
        PRODUCT = "product", "Product QR"

    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="marketing_qrcodes")
    campaign = models.ForeignKey(Campaign, on_delete=models.SET_NULL, null=True, blank=True, related_name="qrcodes")
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.CAMPAIGN, db_index=True)
    target_url = models.URLField(blank=True, default="")
    scan_count = models.IntegerField(default=0)
    last_scanned_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["kind", "created_at"], name="qr_kind_dt_idx"),
            models.Index(fields=["agent", "created_at"], name="qr_agent_dt_idx"),
        ]

    def bump_scan(self):
        from django.utils import timezone

        self.scan_count += 1
        self.last_scanned_at = timezone.now()
        self.save(update_fields=["scan_count", "last_scanned_at", "updated_at"])


class CampaignMessage(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="messages")
    lead = models.ForeignKey("leads.Lead", on_delete=models.SET_NULL, null=True, blank=True, related_name="campaign_messages")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="campaign_messages")

    destination = models.CharField(max_length=120, blank=True, default="")
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    provider_ref = models.CharField(max_length=120, blank=True, default="")
    last_error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["campaign", "status"]),
            models.Index(fields=["status", "created_at"]),
        ]


class CampaignLead(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="campaign_leads")
    lead = models.ForeignKey("leads.Lead", on_delete=models.CASCADE, related_name="campaign_leads")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("campaign", "lead")]
        indexes = [
            models.Index(fields=["campaign", "created_at"]),
            models.Index(fields=["lead", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.campaign_id}:{self.lead_id}"
