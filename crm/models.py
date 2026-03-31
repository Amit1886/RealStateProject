from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone
from decimal import Decimal


class CustomerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="crm_profile")
    company = models.ForeignKey(
        "core_settings.CompanySettings",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="crm_customers",
    )
    last_contacted_at = models.DateTimeField(null=True, blank=True)
    lifecycle_stage = models.CharField(max_length=50, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)

    def __str__(self) -> str:
        return f"{self.user_id}:{self.lifecycle_stage}"


class CustomerNote(models.Model):
    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name="notes")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)


class CallLog(models.Model):
    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name="call_logs", null=True, blank=True)
    lead = models.ForeignKey("leads.Lead", on_delete=models.CASCADE, related_name="call_logs", null=True, blank=True)
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    direction = models.CharField(max_length=10, choices=(("outbound", "Outbound"), ("inbound", "Inbound")))
    phone_number = models.CharField(max_length=20, blank=True, default="")
    duration_seconds = models.PositiveIntegerField(default=0)
    outcome = models.CharField(max_length=80, blank=True, default="")
    telephony_provider = models.CharField(max_length=80, blank=True, default="")
    external_call_id = models.CharField(max_length=120, blank=True, default="")
    recording_url = models.URLField(blank=True, default="")
    missed_call = models.BooleanField(default=False, db_index=True)
    note = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["lead", "created_at"]),
            models.Index(fields=["customer", "created_at"]),
            models.Index(fields=["missed_call", "created_at"]),
        ]


class AdminAlert(models.Model):
    class Severity(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        CRITICAL = "critical", "Critical"

    company = models.ForeignKey(
        "core_settings.CompanySettings",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="admin_alerts",
    )
    title = models.CharField(max_length=160)
    message = models.TextField(blank=True, default="")
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.INFO, db_index=True)
    source = models.CharField(max_length=80, blank=True, default="")
    payload = models.JSONField(default=dict, blank=True)
    resolved = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["company", "severity", "resolved", "created_at"])]


class DashboardCache(models.Model):
    company = models.ForeignKey(
        "core_settings.CompanySettings",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="dashboard_cache",
    )
    key = models.CharField(max_length=80, db_index=True)
    data = models.JSONField(default=dict, blank=True)
    ttl_seconds = models.PositiveIntegerField(default=900)
    refreshed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("company", "key")]
        indexes = [models.Index(fields=["company", "key"])]


class FollowUp(models.Model):
    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name="followups")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=160)
    due_at = models.DateTimeField(db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def mark_done(self):
        if not self.completed_at:
            self.completed_at = timezone.now()
            self.save(update_fields=["completed_at"])


class LocalShop(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        DEMO = "demo", "Demo given"
        CONVERTED = "converted", "Converted"
        LOST = "lost", "Lost"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="local_shops")
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="local_shops_assigned")
    company = models.ForeignKey("core_settings.CompanySettings", on_delete=models.CASCADE, null=True, blank=True, related_name="local_shops")

    shop_name = models.CharField(max_length=180)
    owner_name = models.CharField(max_length=160, blank=True, default="")
    mobile = models.CharField(max_length=20, db_index=True)
    category = models.CharField(max_length=120, blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW, db_index=True)
    referral_code = models.CharField(max_length=40, blank=True, default="")

    metadata = models.JSONField(default=dict, blank=True)
    trial_expires_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner", "status", "created_at"], name="ls_owner_status_idx"),
            models.Index(fields=["agent", "status"], name="ls_agent_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.shop_name} ({self.mobile})"


class OverrideLog(models.Model):
    class ActionType(models.TextChoices):
        PRICE_OVERRIDE = "price_override", "Price Override"
        COMMISSION_OVERRIDE = "commission_override", "Commission Override"
        PAYMENT_ADJUSTMENT = "payment_adjustment", "Payment Adjustment"
        DEAL_STATUS_OVERRIDE = "deal_status_override", "Deal Status Override"
        FEATURE_OVERRIDE = "feature_override", "Feature Override"
        INVENTORY_HOLD = "inventory_hold", "Inventory Hold"

    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="override_logs",
    )
    action_type = models.CharField(max_length=40, choices=ActionType.choices, db_index=True)
    target_model = models.CharField(max_length=120, db_index=True)
    target_object_id = models.CharField(max_length=64, blank=True, default="", db_index=True)
    old_value = models.JSONField(default=dict, blank=True)
    new_value = models.JSONField(default=dict, blank=True)
    reason = models.CharField(max_length=255, blank=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [models.Index(fields=["target_model", "action_type", "timestamp"])]

    def __str__(self) -> str:
        return f"{self.action_type}:{self.target_model}:{self.target_object_id}"


class UnitHold(models.Model):
    class HoldStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        EXPIRED = "expired", "Expired"
        RELEASED = "released", "Released"

    unit = models.ForeignKey("leads.Property", on_delete=models.CASCADE, related_name="holds")
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="unit_holds")
    hold_start = models.DateTimeField(auto_now_add=True, db_index=True)
    hold_end = models.DateTimeField(db_index=True)
    status = models.CharField(max_length=20, choices=HoldStatus.choices, default=HoldStatus.ACTIVE, db_index=True)
    released_at = models.DateTimeField(null=True, blank=True)
    reason = models.CharField(max_length=255, blank=True, default="")
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-hold_start"]
        indexes = [
            models.Index(fields=["unit", "status", "hold_end"]),
            models.Index(fields=["agent", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.unit_id}:{self.status}"


class AgentScore(models.Model):
    agent = models.ForeignKey("agents.Agent", on_delete=models.CASCADE, related_name="gamification_scores")
    score_date = models.DateField(db_index=True)
    leads_assigned = models.PositiveIntegerField(default=0)
    leads_closed = models.PositiveIntegerField(default=0)
    response_time_seconds = models.PositiveIntegerField(default=0)
    points = models.IntegerField(default=0, db_index=True)
    target_points = models.PositiveIntegerField(default=100)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-score_date", "-points", "-created_at"]
        unique_together = [("agent", "score_date")]
        indexes = [
            models.Index(fields=["agent", "score_date"]),
            models.Index(fields=["points", "score_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.agent_id}:{self.score_date}:{self.points}"


class AgentAchievement(models.Model):
    class Kind(models.TextChoices):
        BADGE = "badge", "Badge"
        REWARD = "reward", "Reward"
        RANK = "rank", "Rank"

    agent = models.ForeignKey("agents.Agent", on_delete=models.CASCADE, related_name="achievements")
    code = models.CharField(max_length=80, db_index=True)
    title = models.CharField(max_length=160)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.BADGE, db_index=True)
    description = models.CharField(max_length=255, blank=True, default="")
    points = models.PositiveIntegerField(default=0)
    achieved_at = models.DateTimeField(auto_now_add=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-achieved_at"]
        unique_together = [("agent", "code")]
        indexes = [
            models.Index(fields=["agent", "kind", "achieved_at"]),
            models.Index(fields=["code", "achieved_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.agent_id}:{self.code}"
