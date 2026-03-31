from __future__ import annotations

import secrets
import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


def _generate_idempotency_key() -> str:
    return secrets.token_hex(16)


class PaymentOrder(models.Model):
    class Gateway(models.TextChoices):
        RAZORPAY = "razorpay", "Razorpay"
        STRIPE = "stripe", "Stripe"
        DUMMY = "dummy", "Demo Gateway"

    class Purpose(models.TextChoices):
        WALLET_TOPUP = "wallet_topup", "Wallet Top-Up"
        SUBSCRIPTION = "subscription", "Subscription"
        PROPERTY_BOOKING = "property_booking", "Property Booking"
        SERVICE = "service", "Service Purchase"

    class Status(models.TextChoices):
        CREATED = "created", "Created"
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"
        CANCELLED = "cancelled", "Cancelled"

    reference_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payment_orders")
    wallet = models.ForeignKey(
        "wallet.Wallet",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_orders",
    )
    order = models.ForeignKey(
        "billing.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_orders",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=10, default="INR")
    gateway = models.CharField(max_length=20, choices=Gateway.choices, default=Gateway.DUMMY, db_index=True)
    purpose = models.CharField(max_length=32, choices=Purpose.choices, default=Purpose.WALLET_TOPUP, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CREATED, db_index=True)
    provider_order_id = models.CharField(max_length=120, blank=True, default="", db_index=True)
    provider_payment_id = models.CharField(max_length=120, blank=True, default="", db_index=True)
    signature = models.CharField(max_length=255, blank=True, default="")
    idempotency_key = models.CharField(max_length=120, unique=True, db_index=True, blank=True)
    callback_url = models.URLField(blank=True)
    return_url = models.URLField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["gateway", "status"]),
            models.Index(fields=["purpose", "status"]),
        ]

    def save(self, *args, **kwargs):
        if not self.idempotency_key:
            self.idempotency_key = _generate_idempotency_key()
        super().save(*args, **kwargs)

    def mark_pending(self):
        self.status = self.Status.PENDING
        self.save(update_fields=["status", "updated_at"])

    def mark_paid(self, *, provider_payment_id: str = "", signature: str = ""):
        self.status = self.Status.PAID
        self.provider_payment_id = provider_payment_id or self.provider_payment_id
        self.signature = signature or self.signature
        self.paid_at = timezone.now()
        self.save(update_fields=["status", "provider_payment_id", "signature", "paid_at", "updated_at"])

    def __str__(self) -> str:
        return f"{self.reference_id} | {self.gateway} | {self.amount}"


class PaymentTransaction(models.Model):
    class Mode(models.TextChoices):
        CASH = "cash", "Cash"
        UPI = "upi", "UPI"
        CARD = "card", "Card"
        WALLET = "wallet", "Wallet"
        RAZORPAY = "razorpay", "Razorpay"
        STRIPE = "stripe", "Stripe"
        DEMO = "demo", "Demo"

    class Status(models.TextChoices):
        INITIATED = "initiated", "Initiated"
        AUTHORIZED = "authorized", "Authorized"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    reference_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    payment_order = models.ForeignKey(
        "payments.PaymentOrder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    order = models.ForeignKey(
        "billing.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="payments")
    mode = models.CharField(max_length=20, choices=Mode.choices, default=Mode.DEMO)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.INITIATED, db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=10, default="INR")
    external_ref = models.CharField(max_length=100, blank=True, db_index=True)
    payment_id = models.CharField(max_length=120, blank=True, default="", db_index=True)
    gateway_order_id = models.CharField(max_length=120, blank=True, default="", db_index=True)
    signature = models.CharField(max_length=255, blank=True, default="")
    payload = models.JSONField(default=dict, blank=True)
    credited_to_wallet = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["mode", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.reference_id} | {self.status} | {self.amount}"


class DailyCashSummary(models.Model):
    cashier = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cash_summaries")
    business_date = models.DateField()
    opening_cash = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    cash_in = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    cash_out = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    closing_cash = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        unique_together = ("cashier", "business_date")

    def __str__(self) -> str:
        return f"{self.cashier_id}:{self.business_date}"
