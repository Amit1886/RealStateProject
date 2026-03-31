from __future__ import annotations

from decimal import Decimal
from django.db import models
from saas_core.models import Company


class Commission(models.Model):
    deal = models.OneToOneField("deals.Deal", on_delete=models.CASCADE, related_name="commission")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="commissions", null=True, blank=True)
    admin_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    agent_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    sub_agent_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    settled = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Commission(deal={self.deal_id}, total={self.total_amount})"
