from decimal import Decimal

from django.db import models

from addons.common.models import AuditStampedModel, BranchScopedModel


class AdAccount(BranchScopedModel, AuditStampedModel):
    class Platform(models.TextChoices):
        META = "meta", "Meta Ads"
        GOOGLE = "google", "Google Ads"
        YOUTUBE = "youtube", "YouTube Ads"
        OTT = "ott", "OTT/TV"

    platform = models.CharField(max_length=20, choices=Platform.choices)
    account_id = models.CharField(max_length=120)
    credential_ref = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("platform", "account_id", "branch_code")


class Campaign(BranchScopedModel, AuditStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        COMPLETED = "completed", "Completed"

    account = models.ForeignKey(AdAccount, on_delete=models.CASCADE, related_name="campaigns")
    name = models.CharField(max_length=180)
    external_campaign_id = models.CharField(max_length=120, blank=True)
    objective = models.CharField(max_length=120, blank=True)
    daily_budget = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    starts_on = models.DateField(null=True, blank=True)
    ends_on = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class CampaignMetric(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="metrics")
    metric_date = models.DateField(db_index=True)
    spend = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    impressions = models.PositiveIntegerField(default=0)
    clicks = models.PositiveIntegerField(default=0)
    conversions = models.PositiveIntegerField(default=0)
    revenue = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        unique_together = ("campaign", "metric_date")
        ordering = ["-metric_date"]


class ABExperiment(BranchScopedModel, AuditStampedModel):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="ab_experiments")
    name = models.CharField(max_length=160)
    variant_a = models.JSONField(default=dict, blank=True)
    variant_b = models.JSONField(default=dict, blank=True)
    winner = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
