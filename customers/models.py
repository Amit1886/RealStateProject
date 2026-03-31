from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models


class Customer(models.Model):
    class BuyerType(models.TextChoices):
        BUYER = "buyer", "Buyer"
        SELLER = "seller", "Seller"
        BOTH = "both", "Buyer + Seller"
        TENANT = "tenant", "Tenant"
        LANDLORD = "landlord", "Landlord"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_profile",
    )
    company = models.ForeignKey(
        "saas_core.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="customers",
    )
    assigned_agent = models.ForeignKey(
        "agents.Agent",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customers",
    )
    buyer_type = models.CharField(max_length=20, choices=BuyerType.choices, default=BuyerType.BUYER, db_index=True)
    preferred_location = models.CharField(max_length=160, blank=True, default="")
    preferred_budget = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    property_type = models.CharField(max_length=40, blank=True, default="")
    avatar = models.ImageField(upload_to="customers/avatar/", null=True, blank=True)
    address = models.TextField(blank=True, default="")
    city = models.CharField(max_length=120, blank=True, default="", db_index=True)
    district = models.CharField(max_length=120, blank=True, default="", db_index=True)
    state = models.CharField(max_length=120, blank=True, default="", db_index=True)
    pin_code = models.CharField(max_length=12, blank=True, default="", db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["company", "buyer_type"]),
            models.Index(fields=["assigned_agent", "updated_at"]),
            models.Index(fields=["city", "district", "state", "pin_code"]),
            models.Index(fields=["preferred_budget", "updated_at"]),
        ]

    def __str__(self) -> str:
        return self.user.get_full_name() or self.user.email or f"Customer {self.pk}"


class CustomerPreference(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="preferences")
    property_type = models.CharField(max_length=40, blank=True, default="")
    bedrooms = models.PositiveIntegerField(null=True, blank=True)
    budget_min = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    budget_max = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    city = models.CharField(max_length=120, blank=True, default="", db_index=True)
    district = models.CharField(max_length=120, blank=True, default="", db_index=True)
    state = models.CharField(max_length=120, blank=True, default="", db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-updated_at", "-created_at"]
        indexes = [
            models.Index(fields=["customer", "is_active"]),
            models.Index(fields=["city", "property_type", "bedrooms"]),
            models.Index(fields=["budget_min", "budget_max"]),
        ]

    def __str__(self) -> str:
        return f"{self.customer_id}:{self.property_type or 'preference'}"
