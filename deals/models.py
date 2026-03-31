from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models
from saas_core.models import Company


class Deal(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending"
        WON = "won", "Won"
        LOST = "lost", "Lost"
        CANCELLED = "cancelled", "Cancelled"

    class Stage(models.TextChoices):
        INITIATED = "initiated", "Initiated"
        DOCUMENTATION = "documentation", "Documentation"
        NEGOTIATION = "negotiation", "Negotiation"
        CLOSING = "closing", "Closing"
        CLOSED = "closed", "Closed"

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="deals", null=True, blank=True
    )
    lead = models.OneToOneField("leads.Lead", on_delete=models.CASCADE, related_name="deal")
    customer = models.ForeignKey("customers.Customer", on_delete=models.SET_NULL, null=True, blank=True, related_name="deals")
    property = models.ForeignKey("leads.Property", on_delete=models.SET_NULL, null=True, blank=True, related_name="deals")
    agent = models.ForeignKey("agents.Agent", on_delete=models.CASCADE, related_name="deals")
    deal_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("2.00"))
    company_share_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("50.00"))
    agent_share_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("50.00"))
    commission_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    stage = models.CharField(max_length=20, choices=Stage.choices, default=Stage.INITIATED, db_index=True)
    closing_date = models.DateField(null=True, blank=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["agent", "status"]),
            models.Index(fields=["company", "status", "stage"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["closing_date", "status"]),
        ]

    def __str__(self):
        return f"Deal:{self.pk}:{self.status}"

    def save(self, *args, **kwargs):
        if not self.property_id and getattr(self.lead, "interested_property_id", None):
            self.property_id = self.lead.interested_property_id
        if not self.agent_id and getattr(self.lead, "assigned_agent_id", None):
            self.agent_id = self.lead.assigned_agent_id
        if not self.company_id and getattr(self.lead, "company_id", None):
            self.company_id = self.lead.company_id
        if not self.customer_id and getattr(self.lead, "converted_customer_id", None):
            self.customer_id = self.lead.converted_customer_id
        if self.deal_amount and (not self.commission_amount or self.commission_amount == Decimal("0.00")):
            self.commission_amount = (self.deal_amount * self.commission_rate) / Decimal("100.00")
        super().save(*args, **kwargs)


class Payment(models.Model):
    class PaymentType(models.TextChoices):
        CUSTOMER_PAYMENT = "customer_payment", "Customer Payment"
        AGENT_PAYOUT = "agent_payout", "Agent Payout"
        COMMISSION = "commission", "Commission"
        REFUND = "refund", "Refund"

    class Direction(models.TextChoices):
        INBOUND = "inbound", "Inbound"
        OUTBOUND = "outbound", "Outbound"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="deal_payments", null=True, blank=True)
    deal = models.ForeignKey("deals.Deal", on_delete=models.CASCADE, related_name="payments")
    lead = models.ForeignKey("leads.Lead", on_delete=models.SET_NULL, null=True, blank=True, related_name="payments")
    customer = models.ForeignKey("customers.Customer", on_delete=models.SET_NULL, null=True, blank=True, related_name="payments")
    agent = models.ForeignKey("agents.Agent", on_delete=models.SET_NULL, null=True, blank=True, related_name="payments")
    payment_type = models.CharField(max_length=20, choices=PaymentType.choices, default=PaymentType.CUSTOMER_PAYMENT, db_index=True)
    direction = models.CharField(max_length=10, choices=Direction.choices, default=Direction.INBOUND, db_index=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    adjusted_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    adjustment_note = models.CharField(max_length=255, blank=True, default="")
    adjustment_history = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    reference = models.CharField(max_length=120, blank=True, default="", db_index=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deal_payments_approved",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["deal", "status"]),
            models.Index(fields=["company", "payment_type", "status"]),
            models.Index(fields=["agent", "status"]),
        ]

    def __str__(self):
        return f"Payment:{self.deal_id}:{self.payment_type}:{self.amount}"

    def save(self, *args, **kwargs):
        if not self.company_id and getattr(self.deal, "company_id", None):
            self.company_id = self.deal.company_id
        if not self.lead_id and getattr(self.deal, "lead_id", None):
            self.lead_id = self.deal.lead_id
        if not self.customer_id and getattr(self.deal, "customer_id", None):
            self.customer_id = self.deal.customer_id
        if not self.agent_id and getattr(self.deal, "agent_id", None):
            self.agent_id = self.deal.agent_id
        super().save(*args, **kwargs)


# import Commission model to ensure Django loads it
from .models_commission import Commission  # noqa: E402
