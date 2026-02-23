from decimal import Decimal

from django.conf import settings
from django.db import models


class POSTerminal(models.Model):
    class Mode(models.TextChoices):
        PC = "pc", "PC"
        TABLET = "tablet", "Tablet"
        MOBILE = "mobile", "Mobile"

    name = models.CharField(max_length=100)
    terminal_id = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="pos_terminals")
    mode = models.CharField(max_length=20, choices=Mode.choices, default=Mode.PC)
    shortcuts = models.JSONField(default=dict, blank=True)
    scanner_feedback_sound = models.BooleanField(default=True)
    scanner_feedback_vibration = models.BooleanField(default=True)
    offline_mode_enabled = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class POSSession(models.Model):
    terminal = models.ForeignKey(POSTerminal, on_delete=models.CASCADE, related_name="sessions")
    cashier = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="pos_sessions")
    opening_cash = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    closing_cash = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_open = models.BooleanField(default=True)
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)


class POSHoldBill(models.Model):
    session = models.ForeignKey(POSSession, on_delete=models.CASCADE, related_name="hold_bills")
    hold_code = models.CharField(max_length=30, unique=True)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)


class POSReprintLog(models.Model):
    order = models.ForeignKey("orders.Order", on_delete=models.CASCADE, related_name="pos_reprints")
    cashier = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    reason = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
