from __future__ import annotations

from decimal import Decimal

from django.db import models, transaction
from django.utils import timezone


class AgentWallet(models.Model):
    agent = models.OneToOneField("agents.Agent", on_delete=models.CASCADE, related_name="wallet")
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    total_earned = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    total_withdrawn = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    locked_balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"), help_text="Pending confirmation")
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Wallet:{self.agent_id}:{self.balance}"

    @transaction.atomic
    def credit(self, amount: Decimal, source: str = "manual", note: str = "", status: str = "completed", lock: bool = False):
        amount = Decimal(str(amount or 0))
        WalletTransaction.objects.create(agent=self.agent, amount=amount, type=WalletTransaction.Type.CREDIT, source=source, status=status, note=note)
        if lock:
            self.locked_balance += amount
        else:
            self.balance += amount
            self.total_earned += amount
        self.save(update_fields=["balance", "total_earned", "locked_balance", "updated_at"])

    @transaction.atomic
    def debit(self, amount: Decimal, source: str = "manual", note: str = "", status: str = "completed"):
        amount = Decimal(str(amount or 0))
        WalletTransaction.objects.create(agent=self.agent, amount=amount, type=WalletTransaction.Type.DEBIT, source=source, status=status, note=note)
        self.balance -= amount
        self.total_withdrawn += amount
        self.save(update_fields=["balance", "total_withdrawn", "updated_at"])

    def release_locked(self, amount: Decimal):
        amount = Decimal(str(amount or 0))
        if amount <= 0:
            return
        amount = min(amount, self.locked_balance)
        self.locked_balance -= amount
        self.balance += amount
        self.total_earned += amount
        self.save(update_fields=["locked_balance", "balance", "total_earned", "updated_at"])


class WalletTransaction(models.Model):
    class Type(models.TextChoices):
        CREDIT = "credit", "Credit"
        DEBIT = "debit", "Debit"

    class Source(models.TextChoices):
        LEAD_SALE = "lead_sale", "Lead Sale"
        BONUS = "bonus", "Bonus"
        PENALTY = "penalty", "Penalty"
        ADJUSTMENT = "adjustment", "Adjustment"
        WITHDRAWAL = "withdrawal", "Withdrawal"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    agent = models.ForeignKey("agents.Agent", on_delete=models.CASCADE, related_name="wallet_transactions")
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    type = models.CharField(max_length=10, choices=Type.choices)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.ADJUSTMENT)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.COMPLETED, db_index=True)
    note = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["agent", "status", "created_at"])]

    def __str__(self):
        return f"{self.agent_id}:{self.type}:{self.amount}"
