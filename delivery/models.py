from decimal import Decimal

from django.conf import settings
from django.db import models


class DeliveryAssignment(models.Model):
    class Status(models.TextChoices):
        ASSIGNED = "assigned", "Assigned"
        PICKED = "picked", "Picked"
        EN_ROUTE = "en_route", "En Route"
        DELIVERED = "delivered", "Delivered"
        FAILED = "failed", "Failed"

    order = models.OneToOneField("orders.Order", on_delete=models.CASCADE, related_name="delivery_assignment")
    partner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="deliveries")
    otp_code = models.CharField(max_length=6, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ASSIGNED)
    estimated_distance_km = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    payout_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tracking_payload = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)


class DeliveryTrackingPing(models.Model):
    assignment = models.ForeignKey(DeliveryAssignment, on_delete=models.CASCADE, related_name="pings")
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    speed_kmph = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
