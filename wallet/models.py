from __future__ import annotations

import secrets
import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models


def _generate_wallet_code() -> str:
    return f"WLT{secrets.token_hex(5).upper()}"


class Wallet(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        FROZEN = "frozen", "Frozen"
        CLOSED = "closed", "Closed"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet")
    wallet_uuid = models.UUIDField(editable=False, unique=True, db_index=True, null=True, blank=True)
    wallet_code = models.CharField(max_length=24, unique=True, blank=True, null=True, db_index=True)
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    locked_balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=10, default="INR")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["status", "updated_at"]),
            models.Index(fields=["currency", "status"]),
        ]

    def save(self, *args, **kwargs):
        if not self.wallet_uuid:
            self.wallet_uuid = uuid.uuid4()
        if not self.wallet_code:
            for _ in range(10):
                candidate = _generate_wallet_code()
                if not Wallet.objects.filter(wallet_code=candidate).exclude(pk=self.pk).exists():
                    self.wallet_code = candidate
                    break
        super().save(*args, **kwargs)

    @property
    def available_balance(self) -> Decimal:
        return (self.balance or Decimal("0.00")) - (self.locked_balance or Decimal("0.00"))

    def __str__(self) -> str:
        return f"{self.user_id}:{self.wallet_code or self.wallet_uuid}:{self.balance}"


class WalletAccount(models.Model):
    class AccountType(models.TextChoices):
        BANK = "bank", "Bank"
        UPI = "upi", "UPI"
        WALLET = "wallet", "Wallet"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        VERIFIED = "verified", "Verified"
        DISABLED = "disabled", "Disabled"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet_accounts")
    wallet = models.ForeignKey("wallet.Wallet", on_delete=models.CASCADE, related_name="linked_accounts", null=True, blank=True)
    account_type = models.CharField(max_length=20, choices=AccountType.choices, db_index=True)
    label = models.CharField(max_length=120, blank=True, default="")
    beneficiary_name = models.CharField(max_length=160, blank=True, default="")
    bank_name = models.CharField(max_length=120, blank=True, default="")
    account_number = models.CharField(max_length=50, blank=True, default="")
    ifsc_code = models.CharField(max_length=20, blank=True, default="")
    upi_id = models.CharField(max_length=120, blank=True, default="")
    linked_wallet = models.ForeignKey(
        "wallet.Wallet",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incoming_wallet_links",
    )
    is_default = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-is_default", "-updated_at"]
        indexes = [
            models.Index(fields=["user", "account_type", "status"]),
            models.Index(fields=["upi_id"]),
            models.Index(fields=["account_number", "ifsc_code"]),
        ]

    def __str__(self) -> str:
        return self.label or self.upi_id or self.account_number or f"{self.user_id}:{self.account_type}"


class WalletTransaction(models.Model):
    class EntryType(models.TextChoices):
        CREDIT = "credit", "Credit"
        DEBIT = "debit", "Debit"

    class Source(models.TextChoices):
        MANUAL = "manual", "Manual"
        ADD_MONEY = "add_money", "Add Money"
        TRANSFER = "transfer", "Transfer"
        SERVICE = "service", "Service Deduction"
        REFUND = "refund", "Refund"
        REFERRAL = "referral", "Referral"
        CASHBACK = "cashback", "Cashback"
        REWARD = "reward", "Reward"
        COIN_REDEMPTION = "coin_redemption", "Coin Redemption"
        WITHDRAWAL = "withdrawal", "Withdrawal"
        ADJUSTMENT = "adjustment", "Adjustment"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        REVERSED = "reversed", "Reversed"

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="transactions")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wallet_transactions",
        null=True,
        blank=True,
    )
    counterparty_wallet = models.ForeignKey(
        Wallet,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="counterparty_transactions",
    )
    entry_type = models.CharField(max_length=10, choices=EntryType.choices)
    source = models.CharField(max_length=80, choices=Source.choices, default=Source.MANUAL, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUCCESS, db_index=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    fee_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    reference_id = models.UUIDField(editable=False, unique=True, db_index=True, null=True, blank=True)
    reference = models.CharField(max_length=120, blank=True, default="", db_index=True)
    idempotency_key = models.CharField(max_length=120, blank=True, default="", db_index=True)
    narration = models.CharField(max_length=255, blank=True, default="")
    balance_after = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    locked_balance_after = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    metadata = models.JSONField(default=dict, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["wallet", "created_at"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["source", "status"]),
            models.Index(fields=["reference"]),
            models.Index(fields=["idempotency_key"]),
        ]

    def save(self, *args, **kwargs):
        if not self.reference_id:
            self.reference_id = uuid.uuid4()
        if not self.user_id and self.wallet_id:
            self.user_id = self.wallet.user_id
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.wallet_id}:{self.entry_type}:{self.amount}:{self.reference_id}"


class WalletLedger(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="ledger_entries")
    transaction = models.OneToOneField(WalletTransaction, on_delete=models.CASCADE, related_name="ledger")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="wallet_ledger_actions",
    )
    balance_before = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    balance_after = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    locked_before = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    locked_after = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    available_before = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    available_after = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    note = models.CharField(max_length=255, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["wallet", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.wallet_id}:{self.transaction_id}"


class WalletTransfer(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        REVERSED = "reversed", "Reversed"

    reference_id = models.UUIDField(editable=False, unique=True, db_index=True, null=True, blank=True)
    sender_wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="sent_transfers")
    receiver_wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="received_transfers")
    sender_account = models.ForeignKey(
        WalletAccount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="outgoing_transfers",
    )
    receiver_account = models.ForeignKey(
        WalletAccount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incoming_transfers",
    )
    sender_transaction = models.OneToOneField(
        WalletTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="outgoing_transfer",
    )
    receiver_transaction = models.OneToOneField(
        WalletTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incoming_transfer",
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    fee_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUCCESS, db_index=True)
    note = models.CharField(max_length=255, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["sender_wallet", "created_at"]),
            models.Index(fields=["receiver_wallet", "created_at"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.sender_wallet_id}->{self.receiver_wallet_id}:{self.amount}"

    def save(self, *args, **kwargs):
        if not self.reference_id:
            self.reference_id = uuid.uuid4()
        super().save(*args, **kwargs)


class WithdrawRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        PAID = "paid", "Paid"

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="withdraw_requests")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="withdraw_requests")
    destination_account = models.ForeignKey(
        WalletAccount,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="withdraw_requests",
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    reference_id = models.UUIDField(editable=False, unique=True, db_index=True, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    requested_at = models.DateTimeField(auto_now_add=True, db_index=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="withdraw_processed",
    )
    payout_reference = models.CharField(max_length=120, blank=True, default="")
    rejection_reason = models.CharField(max_length=255, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-requested_at"]
        indexes = [models.Index(fields=["wallet", "status"]), models.Index(fields=["user", "status"])]

    def __str__(self) -> str:
        return f"{self.wallet_id}:{self.amount}:{self.status}"

    def save(self, *args, **kwargs):
        if not self.reference_id:
            self.reference_id = uuid.uuid4()
        super().save(*args, **kwargs)


class WalletAuditLog(models.Model):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="audit_logs")
    transaction = models.ForeignKey(
        WalletTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="wallet_audit_logs",
    )
    action = models.CharField(max_length=80, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["wallet", "created_at"]),
            models.Index(fields=["action", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.wallet_id}:{self.action}:{self.created_at}"
