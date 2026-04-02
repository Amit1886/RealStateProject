from __future__ import annotations

import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from accounts.models import UserProfile as KhataProfile
from wallet.models import (
    Wallet,
    WalletAccount,
    WalletAuditLog,
    WalletLedger,
    WalletTransaction,
    WalletTransfer,
    WithdrawRequest,
)

TWO_PLACES = Decimal("0.01")


def _to_decimal(value: Any) -> Decimal:
    amount = Decimal(str(value or "0")).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    if amount <= 0:
        raise ValueError("Amount must be positive")
    return amount


def get_or_create_wallet(user) -> Wallet:
    wallet, _ = Wallet.objects.get_or_create(user=user)
    if not wallet.wallet_code:
        wallet.save(update_fields=["wallet_code", "updated_at"])
    return wallet


def _find_or_create_synced_account(*, user, wallet, account_type, defaults=None, **lookup):
    defaults = defaults or {}
    queryset = WalletAccount.objects.filter(user=user, account_type=account_type, **lookup).order_by("-is_default", "-updated_at", "id")
    account = queryset.first()
    if account:
        updates = {}
        for field, value in defaults.items():
            if field == "is_default":
                continue
            if value not in (None, "") and getattr(account, field) in (None, ""):
                updates[field] = value
        if not account.wallet_id:
            updates["wallet"] = wallet
        if updates:
            for field, value in updates.items():
                setattr(account, field, value)
            account.save(update_fields=[*updates.keys(), "updated_at"])
        return account, False
    account = WalletAccount.objects.create(
        user=user,
        wallet=wallet,
        account_type=account_type,
        **lookup,
        **defaults,
    )
    return account, True


def sync_profile_payment_accounts(user):
    profile = KhataProfile.objects.filter(user=user).first()
    wallet = get_or_create_wallet(user)
    created_accounts = []
    upi_id = (getattr(profile, "upi_id", "") or "").strip() if profile else ""
    bank_name = (getattr(profile, "bank_name", "") or "").strip() if profile else ""
    account_number = (getattr(profile, "account_number", "") or "").strip() if profile else ""
    ifsc_code = (getattr(profile, "ifsc_code", "") or "").strip() if profile else ""
    if upi_id:
        account, created = _find_or_create_synced_account(
            user=user,
            wallet=wallet,
            account_type=WalletAccount.AccountType.UPI,
            upi_id=upi_id,
            defaults={
                "label": "Primary UPI",
                "beneficiary_name": profile.full_name or user.get_full_name() or user.username or user.email,
                "status": WalletAccount.Status.VERIFIED,
                "is_default": not WalletAccount.objects.filter(user=user, account_type=WalletAccount.AccountType.UPI).exists(),
            },
        )
        if created:
            created_accounts.append(account)
    if account_number:
        account, created = _find_or_create_synced_account(
            user=user,
            wallet=wallet,
            account_type=WalletAccount.AccountType.BANK,
            account_number=account_number,
            ifsc_code=ifsc_code,
            defaults={
                "label": bank_name or "Primary Bank",
                "beneficiary_name": profile.full_name or user.get_full_name() or user.username or user.email,
                "bank_name": bank_name or "",
                "status": WalletAccount.Status.VERIFIED,
                "is_default": not WalletAccount.objects.filter(user=user, account_type=WalletAccount.AccountType.BANK).exists(),
            },
        )
        if created:
            created_accounts.append(account)
    _find_or_create_synced_account(
        user=user,
        wallet=wallet,
        account_type=WalletAccount.AccountType.WALLET,
        linked_wallet=wallet,
        defaults={
            "label": "Internal Wallet",
            "beneficiary_name": user.get_full_name() or user.username or user.email,
            "status": WalletAccount.Status.VERIFIED,
            "is_default": not WalletAccount.objects.filter(user=user, account_type=WalletAccount.AccountType.WALLET).exists(),
        },
    )
    return created_accounts


def create_linked_account(
    user,
    *,
    account_type: str,
    label: str = "",
    beneficiary_name: str = "",
    bank_name: str = "",
    account_number: str = "",
    ifsc_code: str = "",
    upi_id: str = "",
    linked_wallet: Wallet | None = None,
    is_default: bool = False,
    status: str = WalletAccount.Status.PENDING,
    metadata=None,
):
    wallet = get_or_create_wallet(user)
    if is_default:
        WalletAccount.objects.filter(user=user, account_type=account_type, is_default=True).update(is_default=False)
    return WalletAccount.objects.create(
        user=user,
        wallet=wallet,
        account_type=account_type,
        label=label[:120],
        beneficiary_name=beneficiary_name[:160],
        bank_name=bank_name[:120],
        account_number=account_number[:50],
        ifsc_code=ifsc_code[:20],
        upi_id=upi_id[:120],
        linked_wallet=linked_wallet,
        is_default=is_default,
        status=status,
        metadata=metadata or {},
    )


def _resolve_wallet_lock(user) -> Wallet:
    wallet = get_or_create_wallet(user)
    return Wallet.objects.select_for_update().get(pk=wallet.pk)


def _log_audit(wallet: Wallet, *, action: str, actor=None, transaction_obj: WalletTransaction | None = None, metadata=None):
    WalletAuditLog.objects.create(
        wallet=wallet,
        transaction=transaction_obj,
        actor=actor,
        action=action,
        metadata=metadata or {},
    )


def _create_wallet_entry(
    wallet: Wallet,
    *,
    amount: Decimal,
    entry_type: str,
    source: str,
    status: str = WalletTransaction.Status.SUCCESS,
    reference: str = "",
    reference_id: uuid.UUID | None = None,
    idempotency_key: str = "",
    narration: str = "",
    metadata=None,
    actor=None,
    counterparty_wallet: Wallet | None = None,
):
    if wallet.status != Wallet.Status.ACTIVE:
        raise ValueError("Wallet is not active")
    metadata = metadata or {}
    if idempotency_key:
        existing = WalletTransaction.objects.filter(
            wallet=wallet,
            idempotency_key=idempotency_key,
            status=WalletTransaction.Status.SUCCESS,
        ).first()
        if existing:
            return existing
    amount = _to_decimal(amount)
    balance_before = wallet.balance or Decimal("0.00")
    locked_before = wallet.locked_balance or Decimal("0.00")
    available_before = balance_before - locked_before

    if entry_type == WalletTransaction.EntryType.DEBIT:
        if available_before < amount:
            raise ValueError("Insufficient wallet balance")
        wallet.balance = balance_before - amount
    else:
        wallet.balance = balance_before + amount

    wallet.save(update_fields=["balance", "updated_at"])

    transaction_obj = WalletTransaction.objects.create(
        wallet=wallet,
        user=wallet.user,
        counterparty_wallet=counterparty_wallet,
        entry_type=entry_type,
        source=source,
        status=status,
        amount=amount,
        reference_id=reference_id or uuid.uuid4(),
        reference=reference[:120],
        idempotency_key=idempotency_key[:120],
        narration=narration[:255],
        balance_after=wallet.balance,
        locked_balance_after=wallet.locked_balance,
        metadata=metadata,
        processed_at=timezone.now() if status == WalletTransaction.Status.SUCCESS else None,
    )
    WalletLedger.objects.create(
        wallet=wallet,
        transaction=transaction_obj,
        actor=actor,
        balance_before=balance_before,
        balance_after=wallet.balance,
        locked_before=locked_before,
        locked_after=wallet.locked_balance,
        available_before=available_before,
        available_after=wallet.available_balance,
        note=narration[:255],
        metadata=metadata,
    )
    _log_audit(
        wallet,
        action=f"wallet_{entry_type}",
        actor=actor,
        transaction_obj=transaction_obj,
        metadata={"source": source, "amount": str(amount), **metadata},
    )
    return transaction_obj


@transaction.atomic
def credit_wallet(
    user,
    amount: Decimal,
    *,
    source: str = WalletTransaction.Source.MANUAL,
    reference: str = "",
    reference_id: uuid.UUID | None = None,
    idempotency_key: str = "",
    metadata=None,
    narration: str = "",
    actor=None,
    counterparty_wallet: Wallet | None = None,
):
    wallet = _resolve_wallet_lock(user)
    transaction_obj = _create_wallet_entry(
        wallet,
        amount=amount,
        entry_type=WalletTransaction.EntryType.CREDIT,
        source=source,
        reference=reference,
        reference_id=reference_id,
        idempotency_key=idempotency_key,
        metadata=metadata,
        narration=narration,
        actor=actor,
        counterparty_wallet=counterparty_wallet,
    )
    return wallet, transaction_obj


@transaction.atomic
def debit_wallet(
    user,
    amount: Decimal,
    *,
    source: str = WalletTransaction.Source.MANUAL,
    reference: str = "",
    reference_id: uuid.UUID | None = None,
    idempotency_key: str = "",
    metadata=None,
    narration: str = "",
    actor=None,
    counterparty_wallet: Wallet | None = None,
):
    wallet = _resolve_wallet_lock(user)
    transaction_obj = _create_wallet_entry(
        wallet,
        amount=amount,
        entry_type=WalletTransaction.EntryType.DEBIT,
        source=source,
        reference=reference,
        reference_id=reference_id,
        idempotency_key=idempotency_key,
        metadata=metadata,
        narration=narration,
        actor=actor,
        counterparty_wallet=counterparty_wallet,
    )
    return wallet, transaction_obj


def credit(user, amount: Decimal, *, source: str = WalletTransaction.Source.MANUAL, reference: str = "", metadata=None):
    wallet, _ = credit_wallet(user, amount, source=source, reference=reference, metadata=metadata)
    return wallet


def debit(user, amount: Decimal, *, source: str = WalletTransaction.Source.MANUAL, reference: str = "", metadata=None):
    wallet, _ = debit_wallet(user, amount, source=source, reference=reference, metadata=metadata)
    return wallet


@transaction.atomic
def transfer_between_wallets(
    sender_user,
    receiver_user,
    amount: Decimal,
    *,
    note: str = "",
    sender_account: WalletAccount | None = None,
    receiver_account: WalletAccount | None = None,
    metadata=None,
    actor=None,
):
    if sender_user.pk == receiver_user.pk:
        raise ValueError("Sender and receiver cannot be the same")
    amount = _to_decimal(amount)
    sender_wallet = get_or_create_wallet(sender_user)
    receiver_wallet = get_or_create_wallet(receiver_user)
    locked_wallets = list(
        Wallet.objects.select_for_update().filter(pk__in=[sender_wallet.pk, receiver_wallet.pk]).order_by("pk")
    )
    locked_map = {wallet.pk: wallet for wallet in locked_wallets}
    sender_locked = locked_map[sender_wallet.pk]
    receiver_locked = locked_map[receiver_wallet.pk]
    reference_id = uuid.uuid4()

    transfer = WalletTransfer.objects.create(
        sender_wallet=sender_locked,
        receiver_wallet=receiver_locked,
        sender_account=sender_account,
        receiver_account=receiver_account,
        amount=amount,
        note=note[:255],
        status=WalletTransfer.Status.PENDING,
        metadata=metadata or {},
    )
    sender_txn = _create_wallet_entry(
        sender_locked,
        amount=amount,
        entry_type=WalletTransaction.EntryType.DEBIT,
        source=WalletTransaction.Source.TRANSFER,
        reference=str(reference_id),
        idempotency_key=f"transfer:out:{reference_id}",
        metadata={"transfer_id": transfer.id, **(metadata or {})},
        narration=note or f"Transfer to {receiver_user.email}",
        actor=actor,
        counterparty_wallet=receiver_locked,
    )
    receiver_txn = _create_wallet_entry(
        receiver_locked,
        amount=amount,
        entry_type=WalletTransaction.EntryType.CREDIT,
        source=WalletTransaction.Source.TRANSFER,
        reference=str(reference_id),
        idempotency_key=f"transfer:in:{reference_id}",
        metadata={"transfer_id": transfer.id, **(metadata or {})},
        narration=note or f"Transfer from {sender_user.email}",
        actor=actor,
        counterparty_wallet=sender_locked,
    )
    transfer.sender_transaction = sender_txn
    transfer.receiver_transaction = receiver_txn
    transfer.status = WalletTransfer.Status.SUCCESS
    transfer.processed_at = timezone.now()
    transfer.save(update_fields=["sender_transaction", "receiver_transaction", "status", "processed_at"])
    _log_audit(sender_locked, action="wallet_transfer_out", actor=actor, transaction_obj=sender_txn, metadata={"transfer_id": transfer.id})
    _log_audit(receiver_locked, action="wallet_transfer_in", actor=actor, transaction_obj=receiver_txn, metadata={"transfer_id": transfer.id})
    return transfer


@transaction.atomic
def request_withdrawal(user, amount: Decimal, metadata=None, destination_account: WalletAccount | None = None) -> WithdrawRequest:
    wallet = _resolve_wallet_lock(user)
    amount = _to_decimal(amount)
    if wallet.available_balance < amount:
        raise ValueError("Insufficient wallet balance")
    wallet.locked_balance = (wallet.locked_balance or Decimal("0.00")) + amount
    wallet.save(update_fields=["locked_balance", "updated_at"])
    request_obj = WithdrawRequest.objects.create(
        wallet=wallet,
        user=user,
        destination_account=destination_account,
        amount=amount,
        metadata=metadata or {},
    )
    _log_audit(wallet, action="withdraw_requested", actor=user, metadata={"withdraw_request_id": request_obj.id, "amount": str(amount)})
    return request_obj


@transaction.atomic
def approve_withdrawal(request_obj: WithdrawRequest, *, approver, payout_reference: str = ""):
    request_obj = WithdrawRequest.objects.select_for_update().select_related("wallet").get(pk=request_obj.pk)
    if request_obj.status != WithdrawRequest.Status.PENDING:
        return request_obj
    request_obj.status = WithdrawRequest.Status.APPROVED
    request_obj.approved_at = timezone.now()
    request_obj.processed_at = timezone.now()
    request_obj.processed_by = approver
    request_obj.payout_reference = payout_reference[:120]
    request_obj.save(update_fields=["status", "approved_at", "processed_at", "processed_by", "payout_reference"])
    _log_audit(request_obj.wallet, action="withdraw_approved", actor=approver, metadata={"withdraw_request_id": request_obj.id})
    return request_obj


@transaction.atomic
def reject_withdrawal(request_obj: WithdrawRequest, *, approver=None, reason: str = ""):
    request_obj = WithdrawRequest.objects.select_for_update().select_related("wallet").get(pk=request_obj.pk)
    if request_obj.status not in {WithdrawRequest.Status.PENDING, WithdrawRequest.Status.APPROVED}:
        return request_obj
    wallet = Wallet.objects.select_for_update().get(pk=request_obj.wallet_id)
    wallet.locked_balance = max(Decimal("0.00"), (wallet.locked_balance or Decimal("0.00")) - request_obj.amount)
    wallet.save(update_fields=["locked_balance", "updated_at"])
    request_obj.status = WithdrawRequest.Status.REJECTED
    request_obj.rejection_reason = reason[:255]
    request_obj.processed_at = timezone.now()
    request_obj.processed_by = approver
    request_obj.save(update_fields=["status", "rejection_reason", "processed_at", "processed_by"])
    _log_audit(wallet, action="withdraw_rejected", actor=approver, metadata={"withdraw_request_id": request_obj.id, "reason": reason[:255]})
    return request_obj


@transaction.atomic
def mark_withdrawal_paid(request_obj: WithdrawRequest, *, payout_reference: str = "", approver=None):
    request_obj = WithdrawRequest.objects.select_for_update().select_related("wallet").get(pk=request_obj.pk)
    wallet = Wallet.objects.select_for_update().get(pk=request_obj.wallet_id)
    if wallet.locked_balance < request_obj.amount:
        raise ValueError("Locked balance is lower than withdrawal amount")
    wallet.locked_balance = wallet.locked_balance - request_obj.amount
    wallet.balance = wallet.balance - request_obj.amount
    wallet.save(update_fields=["locked_balance", "balance", "updated_at"])
    transaction_obj = WalletTransaction.objects.create(
        wallet=wallet,
        user=wallet.user,
        entry_type=WalletTransaction.EntryType.DEBIT,
        source=WalletTransaction.Source.WITHDRAWAL,
        status=WalletTransaction.Status.SUCCESS,
        amount=request_obj.amount,
        reference=str(request_obj.reference_id),
        narration="Withdrawal paid",
        balance_after=wallet.balance,
        locked_balance_after=wallet.locked_balance,
        metadata={"withdraw_request_id": request_obj.id},
        processed_at=timezone.now(),
    )
    WalletLedger.objects.create(
        wallet=wallet,
        transaction=transaction_obj,
        actor=approver,
        balance_before=wallet.balance + request_obj.amount,
        balance_after=wallet.balance,
        locked_before=wallet.locked_balance + request_obj.amount,
        locked_after=wallet.locked_balance,
        available_before=wallet.balance,
        available_after=wallet.available_balance,
        note="Withdrawal payout settled",
        metadata={"withdraw_request_id": request_obj.id},
    )
    request_obj.status = WithdrawRequest.Status.PAID
    request_obj.payout_reference = payout_reference[:120] or request_obj.payout_reference
    request_obj.processed_at = timezone.now()
    request_obj.processed_by = approver
    request_obj.save(update_fields=["status", "processed_at", "processed_by", "payout_reference"])
    _log_audit(wallet, action="withdraw_paid", actor=approver, transaction_obj=transaction_obj, metadata={"withdraw_request_id": request_obj.id})
    return request_obj


@transaction.atomic
def refund_wallet_transaction(transaction_obj: WalletTransaction, *, actor=None, note: str = ""):
    locked_txn = WalletTransaction.objects.select_for_update().select_related("wallet", "wallet__user").get(pk=transaction_obj.pk)
    if locked_txn.status != WalletTransaction.Status.SUCCESS:
        raise ValueError("Only successful transactions can be refunded")
    refund_entry_type = (
        WalletTransaction.EntryType.CREDIT
        if locked_txn.entry_type == WalletTransaction.EntryType.DEBIT
        else WalletTransaction.EntryType.DEBIT
    )
    wallet = Wallet.objects.select_for_update().get(pk=locked_txn.wallet_id)
    refund_txn = _create_wallet_entry(
        wallet,
        amount=locked_txn.amount,
        entry_type=refund_entry_type,
        source=WalletTransaction.Source.REFUND,
        reference=str(locked_txn.reference_id),
        idempotency_key=f"refund:{locked_txn.reference_id}",
        metadata={"refunded_transaction_id": locked_txn.id},
        narration=note or f"Refund for {locked_txn.reference_id}",
        actor=actor,
        counterparty_wallet=locked_txn.counterparty_wallet,
    )
    locked_txn.status = WalletTransaction.Status.REVERSED
    locked_txn.save(update_fields=["status"])
    _log_audit(wallet, action="wallet_refund", actor=actor, transaction_obj=refund_txn, metadata={"refunded_transaction_id": locked_txn.id})
    return refund_txn


def get_wallet_summary(user):
    wallet = get_or_create_wallet(user)
    sync_profile_payment_accounts(user)
    aggregates = wallet.transactions.aggregate(
        credits=Sum("amount", filter=Q(entry_type=WalletTransaction.EntryType.CREDIT)),
        debits=Sum("amount", filter=Q(entry_type=WalletTransaction.EntryType.DEBIT)),
    )
    return {
        "wallet": wallet,
        "available_balance": wallet.available_balance,
        "total_credit": aggregates["credits"] or Decimal("0.00"),
        "total_debit": aggregates["debits"] or Decimal("0.00"),
        "linked_accounts": wallet.linked_accounts.order_by("-is_default", "-updated_at")[:6],
        "recent_transactions": wallet.transactions.order_by("-created_at")[:10],
        "recent_transfers": wallet.sent_transfers.order_by("-created_at")[:5],
        "withdraw_requests": wallet.withdraw_requests.order_by("-requested_at")[:5],
    }
