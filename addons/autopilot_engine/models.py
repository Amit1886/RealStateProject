from django.conf import settings
from django.db import models

from addons.common.models import AuditStampedModel, BranchScopedModel


class FeatureToggle(AuditStampedModel):
    key = models.CharField(max_length=120, unique=True)
    description = models.CharField(max_length=255, blank=True)
    enabled = models.BooleanField(default=False, db_index=True)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["key"]

    def __str__(self):
        return f"{self.key}: {'on' if self.enabled else 'off'}"


class AutopilotEvent(BranchScopedModel, AuditStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        RETRY = "retry", "Retry"

    event_key = models.CharField(max_length=120, db_index=True)
    source = models.CharField(max_length=120, default="system")
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=3)
    last_error = models.TextField(blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="autopilot_events",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["event_key", "status"])]

    def __str__(self):
        return f"{self.event_key} ({self.status})"


class WorkflowRule(BranchScopedModel, AuditStampedModel):
    name = models.CharField(max_length=160)
    event_key = models.CharField(max_length=120, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    priority = models.PositiveIntegerField(default=100)
    conditions = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["priority", "id"]

    def __str__(self):
        return f"{self.event_key} -> {self.name}"


class WorkflowAction(AuditStampedModel):
    rule = models.ForeignKey(WorkflowRule, on_delete=models.CASCADE, related_name="actions")
    action_key = models.CharField(max_length=120)
    run_order = models.PositiveIntegerField(default=10)
    params = models.JSONField(default=dict, blank=True)
    retry_limit = models.PositiveIntegerField(default=2)
    critical = models.BooleanField(default=False)

    class Meta:
        ordering = ["run_order", "id"]

    def __str__(self):
        return f"{self.rule_id}::{self.action_key}"


class AutopilotExecution(AuditStampedModel):
    class Status(models.TextChoices):
        STARTED = "started", "Started"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    event = models.ForeignKey(AutopilotEvent, on_delete=models.CASCADE, related_name="executions")
    rule = models.ForeignKey(WorkflowRule, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.STARTED, db_index=True)
    failure_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]


class AutopilotStepLog(models.Model):
    class Status(models.TextChoices):
        STARTED = "started", "Started"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    execution = models.ForeignKey(AutopilotExecution, on_delete=models.CASCADE, related_name="steps")
    action_key = models.CharField(max_length=120)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.STARTED)
    response = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)
    attempt = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]


class AutopilotAuditLog(BranchScopedModel):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=160)
    target = models.CharField(max_length=160, blank=True)
    meta = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["branch_code", "action"])]

    def __str__(self):
        return self.action


class BackupJob(AuditStampedModel):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    storage = models.CharField(max_length=120, default="local")
    snapshot_ref = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
