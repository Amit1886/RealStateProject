from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from saas_core.models import Company


class Scheme(models.Model):
    class OwnershipStatus(models.TextChoices):
        FIRST_TIME = "first_time", "First Time Buyer"
        EXISTING_OWNER = "existing_owner", "Existing Owner"
        ANY = "any", "Any"

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="schemes",
    )
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    summary = models.CharField(max_length=240, blank=True, default="")
    description = models.TextField(blank=True, default="")
    state = models.CharField(max_length=120, blank=True, default="", db_index=True)
    district = models.CharField(max_length=120, blank=True, default="", db_index=True)
    city = models.CharField(max_length=120, blank=True, default="", db_index=True)
    income_limit = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    ownership_status = models.CharField(max_length=20, choices=OwnershipStatus.choices, default=OwnershipStatus.ANY)
    apply_url = models.URLField(blank=True, default="")
    active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["title"]
        indexes = [
            models.Index(fields=["company", "active"]),
            models.Index(fields=["state", "district", "city"]),
            models.Index(fields=["ownership_status"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:220]
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title


class UserSchemeMatch(models.Model):
    class Status(models.TextChoices):
        MATCHED = "matched", "Matched"
        SAVED = "saved", "Saved"
        APPLIED = "applied", "Applied"

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="scheme_matches",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="scheme_matches",
    )
    scheme = models.ForeignKey(Scheme, on_delete=models.CASCADE, related_name="matches")
    property = models.ForeignKey(
        "leads.Property",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scheme_matches",
    )
    income = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    location = models.CharField(max_length=160, blank=True, default="")
    ownership_status = models.CharField(max_length=20, blank=True, default="")
    match_score = models.PositiveIntegerField(default=0, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.MATCHED, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-match_score", "-created_at"]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["user", "status"]),
            models.Index(fields=["scheme", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.scheme_id}:{self.match_score}"

