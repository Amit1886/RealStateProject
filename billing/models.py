from django.db import models
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from django.utils.text import slugify
import uuid

class Plan(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    slug = models.SlugField(max_length=50, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)
    groups = models.ManyToManyField(Group, blank=True, related_name="plans")

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
        return self.price == 0


class Invoice(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="billing_invoices"
    )
    plan = models.ForeignKey(
        "Plan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices"
    )
    number = models.CharField(max_length=64, unique=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    # 👇 naye fields (Option 1 ke hisab se)
    description = models.TextField(blank=True, null=True)
    date = models.DateTimeField(default=timezone.now)

    paid = models.BooleanField(default=False)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    payment_reference = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = f"INV-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        if self.paid and not self.paid_at:
            self.paid_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        status = "PAID" if self.paid else "PENDING"
        return f"{self.number} - {self.user} - ₹{self.amount} - {status}"

class Subscription(models.Model):
    STATUS_CHOICES = (("pending", "Pending"), ("active", "Active"), ("cancelled", "Cancelled"))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True, blank=True, related_name="subscriptions")
    invoice = models.OneToOneField(Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name="subscription")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="pending")
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def activate(self):
        self.status = "active"
        self.start_date = self.start_date or timezone.now()
        # if plan has groups, add user to those groups
        if self.plan:
            for g in self.plan.groups.all():
                self.user.groups.add(g)
        self.save()

    def cancel(self):
        self.status = "cancelled"
        # optionally remove groups
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

# ---- add PaymentGateway model ----

class PaymentGateway(models.Model):
    PROVIDER_CHOICES = (
        ('razorpay', 'Razorpay'),
        ('phonepe', 'PhonePe'),
        ('dummy', 'Dummy (test)'),
    )

    name = models.CharField(max_length=80, help_text="Friendly name shown in admin")
    provider = models.CharField(max_length=30, choices=PROVIDER_CHOICES, default='razorpay')
    active = models.BooleanField(default=False)
    # credential fields (store in DB but consider encrypting in production)
    api_key = models.CharField(max_length=255, blank=True, null=True)
    api_secret = models.CharField(max_length=255, blank=True, null=True)
    # additional optional config
    checkout_url = models.URLField(blank=True, null=True, help_text="Optional provider checkout endpoint")
    webhook_secret = models.CharField(max_length=255, blank=True, null=True, help_text="Secret used to validate webhooks")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Payment Gateway"
        verbose_name_plural = "Payment Gateways"

    def __str__(self):
        return f"{self.name} ({self.provider})"