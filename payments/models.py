from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class PaymentOrder(models.Model):
    class Gateway(models.TextChoices):
        RAZORPAY = "razorpay", "Razorpay"
        PHONEPE = "phonepe", "PhonePe"
        STRIPE = "stripe", "Stripe"
        DUMMY = "dummy", "Dummy"

    class Purpose(models.TextChoices):
        WALLET_TOPUP = "wallet_topup", "Wallet Top-up"
        PROPERTY_BOOKING = "property_booking", "Property Booking"
        SERVICE_PURCHASE = "service_purchase", "Service Purchase"
        MANUAL = "manual", "Manual"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    reference_id = models.CharField(max_length=64, unique=True, default="", blank=True, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payment_orders")
    wallet = models.ForeignKey("wallet.Wallet", on_delete=models.SET_NULL, null=True, blank=True, related_name="payment_orders")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="INR")
    gateway = models.CharField(max_length=20, choices=Gateway.choices, default=Gateway.DUMMY, db_index=True)
    purpose = models.CharField(max_length=40, choices=Purpose.choices, default=Purpose.MANUAL, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        db_table = "payments_paymentorder"

    def save(self, *args, **kwargs):
        if not self.reference_id:
            self.reference_id = f"PO-{uuid.uuid4().hex[:12].upper()}"
        super().save(*args, **kwargs)

    def mark_paid(self, provider_payment_id: str | None = None):
        self.status = self.Status.PAID
        self.paid_at = self.paid_at or timezone.now()
        if provider_payment_id:
            data = dict(self.metadata or {})
            data["provider_payment_id"] = provider_payment_id
            self.metadata = data
        self.save(update_fields=["status", "paid_at", "metadata", "updated_at"])

    def __str__(self):
        return f"{self.reference_id} - {self.user}"
