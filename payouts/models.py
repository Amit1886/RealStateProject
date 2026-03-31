from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class Payout(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        PAID = "paid", "Paid"
        REJECTED = "rejected", "Rejected"

    agent = models.ForeignKey("agents.Agent", on_delete=models.CASCADE, related_name="payouts")
    lead = models.ForeignKey("leads.Lead", on_delete=models.SET_NULL, null=True, blank=True, related_name="payouts")
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=8, default="INR")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True)
    approval_notes = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    fraud_flag = models.BooleanField(default=False, db_index=True)
    is_withheld = models.BooleanField(default=False, db_index=True)
    blocked_reason = models.CharField(max_length=200, blank=True, default="")

    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payouts_generated",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payouts_approved",
    )

    generated_at = models.DateTimeField(auto_now_add=True, db_index=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-generated_at"]
        indexes = [
            models.Index(fields=["agent", "status"]),
            models.Index(fields=["status", "generated_at"]),
        ]

    def __str__(self) -> str:
        return f"Payout #{self.pk} -> {self.agent_id} ({self.status})"

    def approve(self, user=None, notes: str = ""):
        self.status = self.Status.APPROVED
        self.approved_by = user
        self.approval_notes = notes or self.approval_notes
        self.approved_at = timezone.now()
        self.save(update_fields=["status", "approved_by", "approval_notes", "approved_at", "updated_at"])

    def mark_paid(self, user=None, external_ref: str | None = None):
        self.status = self.Status.PAID
        self.approved_by = self.approved_by or user
        self.paid_at = timezone.now()
        if external_ref:
            meta = self.metadata or {}
            meta["payment_ref"] = external_ref
            self.metadata = meta
        self.save(update_fields=["status", "approved_by", "paid_at", "metadata", "updated_at"])
