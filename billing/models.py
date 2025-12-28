from django.db import models
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth.models import Group
from django.utils.text import slugify
from decimal import Decimal
from khataapp.models import Party


# =========================
# 🎛 FEATURE TOGGLE MODEL
# =========================
class FeatureToggle(models.Model):
    allow_credit_report = models.BooleanField(default=False)
    allow_whatsapp = models.BooleanField(default=False)
    allow_pdf_report = models.BooleanField(default=False)
    allow_commerce = models.BooleanField(default=False)

    def __str__(self):
        return f"Features (Commerce: {'ON' if self.allow_commerce else 'OFF'})"


# =========================
# 💎 PLAN MODEL
# =========================
class Plan(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    slug = models.SlugField(max_length=50, unique=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    groups = models.ManyToManyField(Group, blank=True, related_name="plans")

    feature_toggle = models.OneToOneField(
        "billing.FeatureToggle",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="plan"
    )

    class Meta:
        ordering = ["price"]

    def __str__(self):
        return f"{self.name} - ₹{self.price}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def is_free(self):
        return self.price == Decimal("0.00")


# =========================
# 🧾 INVOICE MODEL
# =========================
class BillingInvoice(models.Model):
    STATUS_CHOICES = [
        ('unpaid', 'Unpaid'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="billing_invoices"
    )
    plan = models.ForeignKey(
        Plan, on_delete=models.CASCADE, related_name="billing_invoices"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    invoice_number = models.CharField(max_length=20, unique=True, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='unpaid'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        """Auto-generate unique invoice number."""
        if not self.invoice_number:
            last = BillingInvoice.objects.order_by('-id').first()
            next_num = (last.id + 1) if last else 1
            self.invoice_number = f"BILL-{next_num:05d}"
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("billing:payment_page", args=[self.invoice_number])

    def __str__(self):
        return f"{self.invoice_number} - {self.user}"


# =========================
# 📦 SUBSCRIPTION MODEL
# =========================
class Subscription(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("active", "Active"),
        ("cancelled", "Cancelled"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, related_name="billing_subscriptions"
    )
    plan = models.ForeignKey(
        Plan, on_delete=models.SET_NULL, null=True, blank=True, related_name="billing_subscriptions"
    )
    invoice = models.OneToOneField(
        BillingInvoice,  # ✅ Corrected here!
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="billing_subscription"
    )
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="pending")
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def activate(self):
        self.status = "active"
        self.start_date = self.start_date or timezone.now()
        if self.plan:
            for g in self.plan.groups.all():
                self.user.groups.add(g)
        self.save()

    def cancel(self):
        self.status = "cancelled"
        if self.plan:
            for g in self.plan.groups.all():
                try:
                    self.user.groups.remove(g)
                except Exception:
                    pass
        self.save()

    @property
    def is_active(self):
        return self.status == "active"

    def __str__(self):
        return f"Subscription: {self.user} → {self.plan} [{self.status}]"

# =========================
# 🏦 PAYMENT GATEWAY MODEL
# =========================
class PaymentGateway(models.Model):
    PROVIDER_CHOICES = (
        ('razorpay', 'Razorpay'),
        ('phonepe', 'PhonePe'),
        ('dummy', 'Dummy (Test Gateway)'),
    )

    name = models.CharField(max_length=80)
    provider = models.CharField(max_length=30, choices=PROVIDER_CHOICES, default='dummy')
    active = models.BooleanField(default=False)

    api_key = models.CharField(max_length=255, blank=True, null=True)
    api_secret = models.CharField(max_length=255, blank=True, null=True)
    checkout_url = models.URLField(blank=True, null=True)
    webhook_secret = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Payment Gateway"
        verbose_name_plural = "Payment Gateways"

    def __str__(self):
        return f"{self.name} ({self.provider})"


# =========================
# 🏬 COMMERCE & BILLING
# =========================
class Commerce(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, related_name='billing_commerces')
    business_name = models.CharField(max_length=200)
    category = models.CharField(max_length=100, blank=True, null=True)
    gst_number = models.CharField(max_length=50, blank=True, null=True)
    contact_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.business_name} ({self.user.username})"


class Payment(models.Model):
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='billing_payments', null=True, blank=True)
    party = models.ForeignKey(Party, on_delete=models.CASCADE, related_name="payments")  # ADD THIS FIELD
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=100, default='Cash')
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment #{self.id} - {self.payment_status}"


class Order(models.Model):
    ORDER_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='billing_orders')
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payment_status = models.CharField(max_length=20, default='unpaid')
    delivered_at = models.DateTimeField(null=True, blank=True)

    def update_total(self):
        """Auto calculate total_amount from OrderItems"""
        items = self.billing_items.all()
        self.total_amount = sum(item.price * item.quantity for item in items)

    def save(self, *args, **kwargs):
        # 🔥 Auto calculate total every time
        if self.pk:
            self.update_total()

        # 🔥 If delivered
        if self.status == "delivered":
            self.payment_status = "paid"
            if not self.delivered_at:
                self.delivered_at = timezone.now()

        # 🔥 If cancelled
        if self.status == "cancelled":
            self.payment_status = "refunded"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"


class OrderItem(models.Model):
    order = models.ForeignKey("billing.Order", on_delete=models.CASCADE, related_name="billing_items")
    product_name = models.CharField(max_length=255)
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product_name} (x{self.quantity})"


class Warehouse(models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=255, blank=True, null=True)
    capacity = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name


class Stock(models.Model):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='billing_stocks')
    product_name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product_name} ({self.quantity})"


class ChatThread(models.Model):
    user1 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='billing_chat_user1'
    )
    user2 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='billing_chat_user2'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chat between {self.user1} and {self.user2}"


class ChatMessage(models.Model):
    thread = models.ForeignKey(ChatThread, on_delete=models.CASCADE, related_name='billing_messages')
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='billing_sent_messages'
    )
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.sender}: {self.message[:30]}"


class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="billing_notifications"
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return self.title


class PartyPortal(models.Model):
    name = models.CharField(max_length=100)
    link = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name