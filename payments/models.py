from decimal import Decimal

from django.conf import settings
from django.db import models


class PaymentTransaction(models.Model):
    class Mode(models.TextChoices):
        CASH = "cash", "Cash"
        UPI = "upi", "UPI"
        CARD = "card", "Card"
        WALLET = "wallet", "Wallet"
        RAZORPAY = "razorpay", "Razorpay"

    class Status(models.TextChoices):
        INITIATED = "initiated", "Initiated"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    order = models.ForeignKey("orders.Order", on_delete=models.SET_NULL, null=True, blank=True, related_name="payments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="payments")
    mode = models.CharField(max_length=20, choices=Mode.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.INITIATED)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    external_ref = models.CharField(max_length=100, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class DailyCashSummary(models.Model):
    cashier = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cash_summaries")
    business_date = models.DateField()
    opening_cash = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    cash_in = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    cash_out = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    closing_cash = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        unique_together = ("cashier", "business_date")
