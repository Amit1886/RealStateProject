from decimal import Decimal

from django.conf import settings
from django.db import models


class UserRole(models.TextChoices):
    ADMIN = "admin", "Admin"
    B2B_CUSTOMER = "b2b_customer", "B2B Customer"
    B2C_CUSTOMER = "b2c_customer", "B2C Customer"
    SALESMAN = "salesman", "Salesman"
    DELIVERY_PARTNER = "delivery_partner", "Delivery Partner"
    WAREHOUSE_STAFF = "warehouse_staff", "Warehouse Staff"
    POS_CASHIER = "pos_cashier", "POS Cashier"


class UserProfileExt(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saas_profile")
    role = models.CharField(max_length=40, choices=UserRole.choices, default=UserRole.B2C_CUSTOMER, db_index=True)

    wallet_balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    credit_balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    commission_earned = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    printer_preferences = models.JSONField(default=dict, blank=True)
    scanner_preferences = models.JSONField(default=dict, blank=True)
    pos_layout_preferences = models.JSONField(default=dict, blank=True)

    is_active_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["role"]),
            models.Index(fields=["updated_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.role}"


class WalletLedger(models.Model):
    class EntryType(models.TextChoices):
        CREDIT = "credit", "Credit"
        DEBIT = "debit", "Debit"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet_entries")
    entry_type = models.CharField(max_length=10, choices=EntryType.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    source = models.CharField(max_length=60, default="manual")
    reference = models.CharField(max_length=80, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["source"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.entry_type}:{self.amount}"


class CommissionLedger(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="commission_entries")
    order_id = models.CharField(max_length=50, db_index=True)
    role = models.CharField(max_length=40, choices=UserRole.choices)
    margin = models.DecimalField(max_digits=14, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=14, decimal_places=2)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["order_id", "role"])]

    def __str__(self) -> str:
        return f"{self.order_id}:{self.role}:{self.commission_amount}"
