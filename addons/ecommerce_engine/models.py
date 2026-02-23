from decimal import Decimal

from django.db import models

from addons.common.models import AuditStampedModel, BranchScopedModel


class StorefrontProduct(BranchScopedModel, AuditStampedModel):
    product = models.ForeignKey("commerce.Product", on_delete=models.SET_NULL, null=True, blank=True)
    product_name = models.CharField(max_length=200)
    sku = models.CharField(max_length=64)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    available_stock = models.IntegerField(default=0)
    selected_for_online = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False)

    class Meta:
        unique_together = ("branch_code", "sku")
        indexes = [models.Index(fields=["selected_for_online", "is_published"])]


class StorefrontOrder(BranchScopedModel, AuditStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        PACKED = "packed", "Packed"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"

    order_number = models.CharField(max_length=60, unique=True)
    customer_name = models.CharField(max_length=120)
    customer_phone = models.CharField(max_length=20)
    currency = models.CharField(max_length=10, default="INR")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    payment_gateway = models.CharField(max_length=30, blank=True)
    payment_ref = models.CharField(max_length=120, blank=True)
    synced_to_billing = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]


class StorefrontOrderItem(models.Model):
    order = models.ForeignKey(StorefrontOrder, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(StorefrontProduct, on_delete=models.PROTECT, related_name="order_items")
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))


class StorefrontSyncLog(models.Model):
    direction = models.CharField(max_length=20, choices=(("billing_to_store", "Billing->Store"), ("store_to_billing", "Store->Billing")))
    ref = models.CharField(max_length=120)
    status = models.CharField(max_length=20, default="queued")
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class StorefrontPayment(BranchScopedModel, AuditStampedModel):
    class Status(models.TextChoices):
        INITIATED = "initiated", "Initiated"
        CAPTURED = "captured", "Captured"
        FAILED = "failed", "Failed"

    order = models.ForeignKey(StorefrontOrder, on_delete=models.CASCADE, related_name="payments")
    gateway = models.CharField(max_length=30, default="razorpay")
    payment_ref = models.CharField(max_length=120)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=10, default="INR")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.INITIATED, db_index=True)
    raw_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["gateway", "payment_ref"])]


class PaymentGatewayConfig(BranchScopedModel, AuditStampedModel):
    class Provider(models.TextChoices):
        RAZORPAY = "razorpay", "Razorpay"
        STRIPE = "stripe", "Stripe"
        OTHER = "other", "Other"

    provider = models.CharField(max_length=40, choices=Provider.choices, default=Provider.RAZORPAY)
    is_active = models.BooleanField(default=True, db_index=True)
    sandbox = models.BooleanField(default=True)

    # Demo / configuration fields (optional).
    key_id = models.CharField(max_length=200, blank=True)
    key_secret = models.CharField(max_length=200, blank=True)
    webhook_secret = models.CharField(max_length=200, blank=True)
    extra = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("branch_code", "provider")
        ordering = ["branch_code", "provider"]
