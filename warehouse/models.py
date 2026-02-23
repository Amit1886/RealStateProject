from django.conf import settings
from django.db import models


class Warehouse(models.Model):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=30, unique=True)
    address = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    capacity_units = models.PositiveIntegerField(default=0)
    is_dark_store = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["is_dark_store", "is_active"])]

    def __str__(self):
        return f"{self.code} - {self.name}"


class WarehouseStaffAssignment(models.Model):
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="staff_assignments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="warehouse_assignments")
    is_primary = models.BooleanField(default=False)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("warehouse", "user")
        indexes = [models.Index(fields=["warehouse", "is_primary"])]

    def __str__(self):
        return f"{self.warehouse_id}:{self.user_id}"
