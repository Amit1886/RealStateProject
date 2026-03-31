from __future__ import annotations

from django.conf import settings
from django.db import models


class Company(models.Model):
    name = models.CharField(max_length=160)
    domain = models.CharField(max_length=160, blank=True, default="")
    settings = models.JSONField(default=dict, blank=True)
    timezone = models.CharField(max_length=64, default="UTC")
    currency = models.CharField(max_length=8, default="INR")
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    logo = models.ImageField(upload_to="company/logo/", null=True, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class UserCompanyMixin(models.Model):
    """
    Abstract mixin to attach a record to a tenant company.
    """

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="%(app_label)s_%(class)s"
    )

    class Meta:
        abstract = True
