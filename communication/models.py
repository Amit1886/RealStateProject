from __future__ import annotations

from django.conf import settings
from django.db import models


class MessageLog(models.Model):
    class MessageType(models.TextChoices):
        IN_APP = "in_app", "In-App"
        WHATSAPP = "whatsapp", "WhatsApp"
        CHAT = "chat", "Chat"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    company = models.ForeignKey(
        "saas_core.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="message_logs",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="messages_sent",
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="messages_received",
    )
    lead = models.ForeignKey(
        "leads.Lead",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="message_logs",
    )
    message_type = models.CharField(max_length=20, choices=MessageType.choices, default=MessageType.CHAT, db_index=True)
    message = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    provider = models.CharField(max_length=80, blank=True, default="")
    provider_ref = models.CharField(max_length=120, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "message_type", "status"]),
            models.Index(fields=["receiver", "created_at"]),
            models.Index(fields=["lead", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.message_type}:{self.status}:{self.pk}"


class EmailLog(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    company = models.ForeignKey(
        "saas_core.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="email_logs",
    )
    sender = models.EmailField(blank=True, default="")
    recipient = models.EmailField(db_index=True)
    subject = models.CharField(max_length=200, blank=True, default="")
    body = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    provider = models.CharField(max_length=80, blank=True, default="")
    provider_ref = models.CharField(max_length=120, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "status", "created_at"]),
            models.Index(fields=["recipient", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.recipient}:{self.status}"


class SMSLog(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    company = models.ForeignKey(
        "saas_core.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="sms_logs",
    )
    phone = models.CharField(max_length=20, db_index=True)
    message = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    provider = models.CharField(max_length=80, blank=True, default="")
    provider_ref = models.CharField(max_length=120, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "status", "created_at"]),
            models.Index(fields=["phone", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.phone}:{self.status}"
