from __future__ import annotations

from django.db import models

from addons.common.models import AuditStampedModel, BranchScopedModel


class CourierProvider(models.TextChoices):
    SHIPROCKET = "shiprocket", "Shiprocket"
    DELHIVERY = "delhivery", "Delhivery"
    DTDC = "dtdc", "DTDC"


class CourierProviderConfig(BranchScopedModel, AuditStampedModel):
    provider = models.CharField(max_length=40, choices=CourierProvider.choices)
    is_active = models.BooleanField(default=True, db_index=True)
    sandbox = models.BooleanField(default=True)
    base_url = models.URLField(blank=True)
    api_key = models.CharField(max_length=255, blank=True)
    api_secret = models.CharField(max_length=255, blank=True)
    extra = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("branch_code", "provider")
        ordering = ["branch_code", "provider"]


class Shipment(BranchScopedModel, AuditStampedModel):
    class Status(models.TextChoices):
        CREATED = "created", "Created"
        BOOKED = "booked", "Booked"
        IN_TRANSIT = "in_transit", "In Transit"
        DELIVERED = "delivered", "Delivered"
        RTO = "rto", "RTO"
        FAILED = "failed", "Failed"

    provider = models.CharField(max_length=40, choices=CourierProvider.choices, default=CourierProvider.SHIPROCKET)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CREATED, db_index=True)
    ref_type = models.CharField(max_length=40, default="storefront_order", db_index=True)
    ref = models.CharField(max_length=80, db_index=True)  # e.g. storefront order_number
    awb = models.CharField(max_length=80, blank=True)
    tracking_number = models.CharField(max_length=120, blank=True)
    tracking_url = models.URLField(blank=True)
    meta = models.JSONField(default=dict, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["provider", "status"])]


class ShipmentEvent(models.Model):
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=80)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

