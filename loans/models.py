from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from saas_core.models import Company


class Bank(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="banks",
    )
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    logo = models.ImageField(upload_to="banks/logos/", null=True, blank=True)
    website = models.URLField(blank=True, default="")
    support_email = models.EmailField(blank=True, default="")
    support_phone = models.CharField(max_length=30, blank=True, default="")
    active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["company", "active"]),
            models.Index(fields=["slug"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:180]
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class LoanProduct(models.Model):
    class PropertyType(models.TextChoices):
        HOUSE = "house", "House"
        FLAT = "flat", "Flat"
        APARTMENT = "apartment", "Apartment"
        VILLA = "villa", "Villa"
        LAND = "land", "Land"
        COMMERCIAL = "commercial", "Commercial"

    bank = models.ForeignKey(Bank, on_delete=models.CASCADE, related_name="products")
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="loan_products",
    )
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    property_type = models.CharField(max_length=20, choices=PropertyType.choices, blank=True, default="")
    interest_rate = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("8.50"))
    loan_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    tenure_years = models.PositiveIntegerField(default=20)
    emi_estimate = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    min_income_required = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    active = models.BooleanField(default=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["bank__name", "name"]
        indexes = [
            models.Index(fields=["company", "active"]),
            models.Index(fields=["property_type", "active"]),
            models.Index(fields=["interest_rate"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.bank.name}-{self.name}")[:180]
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.bank.name} - {self.name}"


class LoanApplication(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        APPLIED = "applied", "Applied"
        ELIGIBLE = "eligible", "Eligible"
        UNDER_REVIEW = "under_review", "Under Review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="loan_applications",
    )
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="loan_applications",
    )
    property = models.ForeignKey(
        "leads.Property",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="loan_applications",
    )
    loan_product = models.ForeignKey(
        LoanProduct,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applications",
    )
    requested_amount = models.DecimalField(max_digits=14, decimal_places=2)
    tenure_years = models.PositiveIntegerField(default=20)
    monthly_income = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    existing_emi = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    emi_estimate = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    eligibility_ratio = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.APPLIED, db_index=True)
    notes = models.TextField(blank=True, default="")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "status", "created_at"]),
            models.Index(fields=["applicant", "status"]),
            models.Index(fields=["property", "status"]),
        ]

    def mark_reviewed(self, status: str):
        self.status = status
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "reviewed_at", "updated_at"])

    def __str__(self) -> str:
        return f"{self.applicant_id}:{self.requested_amount}:{self.status}"

