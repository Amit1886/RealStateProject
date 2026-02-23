from decimal import Decimal

from django.db import models


class CommissionRule(models.Model):
    name = models.CharField(max_length=100, unique=True)
    salesman_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    delivery_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class CommissionPayout(models.Model):
    order = models.ForeignKey("orders.Order", on_delete=models.CASCADE, related_name="commission_payouts")
    rule = models.ForeignKey(CommissionRule, on_delete=models.SET_NULL, null=True)
    margin_amount = models.DecimalField(max_digits=14, decimal_places=2)
    salesman_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    delivery_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    company_profit = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["order", "created_at"])]
