from __future__ import annotations

from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone


class Party(models.Model):
    """Minimal party stub to satisfy legacy foreign keys."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="khata_parties"
    )
    name = models.CharField(max_length=255)
    mobile = models.CharField(max_length=20, blank=True, default="")
    whatsapp_number = models.CharField(max_length=20, blank=True, default="")
    party_type = models.CharField(max_length=20, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="khata_stub_profile")
    full_name = models.CharField(max_length=255, blank=True, default="")
    mobile = models.CharField(max_length=20, blank=True, default="")
    plan = models.ForeignKey("billing.Plan", on_delete=models.SET_NULL, null=True, blank=True, related_name="khata_profiles")
    created_from = models.CharField(max_length=50, blank=True, default="")
    business_name = models.CharField(max_length=255, blank=True, default="")
    business_type = models.CharField(max_length=100, blank=True, default="")
    address = models.CharField(max_length=255, blank=True, default="")
    gst_number = models.CharField(max_length=50, blank=True, default="")
    profile_picture = models.ImageField(upload_to="profiles/", null=True, blank=True)
    bank_name = models.CharField(max_length=120, blank=True, default="")
    account_number = models.CharField(max_length=50, blank=True, default="")
    ifsc_code = models.CharField(max_length=20, blank=True, default="")
    upi_id = models.CharField(max_length=120, blank=True, default="")
    qr_code = models.ImageField(upload_to="profiles/qr/", null=True, blank=True)

    def __str__(self):
        return self.full_name or self.user.username


class CompanySettings(models.Model):
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="company_settings")
    company_name = models.CharField(max_length=255, blank=True, default="")
    default_plan = models.ForeignKey("billing.Plan", null=True, blank=True, on_delete=models.SET_NULL)
    auto_sms_send = models.BooleanField(default=False)

    def __str__(self):
        return self.company_name or f"CompanySettings({self.owner_id})"


class CreditAccount(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="credit_accounts"
    )
    name = models.CharField(max_length=255)
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class FieldAgent(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="field_agents"
    )
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Transaction(models.Model):
    class TxnType(models.TextChoices):
        CREDIT = "credit", "Credit"
        DEBIT = "debit", "Debit"

    party = models.ForeignKey(Party, on_delete=models.SET_NULL, null=True, blank=True, related_name="transactions")
    txn_type = models.CharField(max_length=10, choices=TxnType.choices)
    txn_mode = models.CharField(max_length=20, blank=True, default="")
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    date = models.DateField(default=timezone.now)
    notes = models.CharField(max_length=255, blank=True, default="")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="khata_transactions"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.txn_type} {self.amount}"


class CollectorVisit(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class LoginLink(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)


class OfflineMessage(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)


class ReminderLog(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
