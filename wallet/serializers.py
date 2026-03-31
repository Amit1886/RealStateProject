from rest_framework import serializers

from wallet.models import (
    Wallet,
    WalletAccount,
    WalletAuditLog,
    WalletLedger,
    WalletTransaction,
    WalletTransfer,
    WithdrawRequest,
)


class WalletSerializer(serializers.ModelSerializer):
    available_balance = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Wallet
        fields = [
            "id",
            "user",
            "wallet_uuid",
            "wallet_code",
            "balance",
            "locked_balance",
            "available_balance",
            "currency",
            "status",
            "metadata",
            "updated_at",
            "created_at",
        ]
        read_only_fields = ["wallet_uuid", "wallet_code", "balance", "locked_balance", "available_balance", "updated_at", "created_at"]


class WalletAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletAccount
        fields = [
            "id",
            "user",
            "wallet",
            "account_type",
            "label",
            "beneficiary_name",
            "bank_name",
            "account_number",
            "ifsc_code",
            "upi_id",
            "linked_wallet",
            "is_default",
            "status",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["user", "wallet", "created_at", "updated_at"]


class WalletTransactionSerializer(serializers.ModelSerializer):
    wallet_code = serializers.CharField(source="wallet.wallet_code", read_only=True)
    counterparty_wallet_code = serializers.CharField(source="counterparty_wallet.wallet_code", read_only=True)

    class Meta:
        model = WalletTransaction
        fields = [
            "id",
            "wallet",
            "wallet_code",
            "user",
            "counterparty_wallet",
            "counterparty_wallet_code",
            "entry_type",
            "source",
            "status",
            "amount",
            "fee_amount",
            "reference_id",
            "reference",
            "idempotency_key",
            "narration",
            "balance_after",
            "locked_balance_after",
            "metadata",
            "processed_at",
            "created_at",
        ]
        read_only_fields = ["reference_id", "balance_after", "locked_balance_after", "processed_at", "created_at"]


class WalletLedgerSerializer(serializers.ModelSerializer):
    transaction_reference = serializers.UUIDField(source="transaction.reference_id", read_only=True)

    class Meta:
        model = WalletLedger
        fields = [
            "id",
            "wallet",
            "transaction",
            "transaction_reference",
            "actor",
            "balance_before",
            "balance_after",
            "locked_before",
            "locked_after",
            "available_before",
            "available_after",
            "note",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields


class WalletTransferSerializer(serializers.ModelSerializer):
    sender_wallet_code = serializers.CharField(source="sender_wallet.wallet_code", read_only=True)
    receiver_wallet_code = serializers.CharField(source="receiver_wallet.wallet_code", read_only=True)

    class Meta:
        model = WalletTransfer
        fields = [
            "id",
            "reference_id",
            "sender_wallet",
            "sender_wallet_code",
            "receiver_wallet",
            "receiver_wallet_code",
            "sender_account",
            "receiver_account",
            "sender_transaction",
            "receiver_transaction",
            "amount",
            "fee_amount",
            "status",
            "note",
            "metadata",
            "processed_at",
            "created_at",
        ]
        read_only_fields = ["reference_id", "sender_transaction", "receiver_transaction", "processed_at", "created_at"]


class WithdrawRequestSerializer(serializers.ModelSerializer):
    wallet_code = serializers.CharField(source="wallet.wallet_code", read_only=True)

    class Meta:
        model = WithdrawRequest
        fields = [
            "id",
            "wallet",
            "wallet_code",
            "user",
            "destination_account",
            "amount",
            "reference_id",
            "status",
            "requested_at",
            "approved_at",
            "processed_at",
            "processed_by",
            "payout_reference",
            "rejection_reason",
            "metadata",
        ]
        read_only_fields = [
            "wallet",
            "wallet_code",
            "user",
            "reference_id",
            "status",
            "requested_at",
            "approved_at",
            "processed_at",
            "processed_by",
            "payout_reference",
            "rejection_reason",
        ]


class WalletAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletAuditLog
        fields = ["id", "wallet", "transaction", "actor", "action", "ip_address", "user_agent", "metadata", "created_at"]
        read_only_fields = fields


class WalletAmountActionSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    source = serializers.CharField(max_length=80, required=False, allow_blank=True)
    reference = serializers.CharField(max_length=120, required=False, allow_blank=True)
    narration = serializers.CharField(max_length=255, required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False)


class WalletTransferActionSerializer(serializers.Serializer):
    recipient_wallet_code = serializers.CharField(max_length=24, required=False, allow_blank=True)
    recipient_user_id = serializers.IntegerField(required=False)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    note = serializers.CharField(max_length=255, required=False, allow_blank=True)
    sender_account_id = serializers.IntegerField(required=False)
    receiver_account_id = serializers.IntegerField(required=False)
    metadata = serializers.JSONField(required=False)


class WalletStatementRequestSerializer(serializers.Serializer):
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    entry_type = serializers.CharField(max_length=10, required=False, allow_blank=True)
    source = serializers.CharField(max_length=80, required=False, allow_blank=True)
    format = serializers.ChoiceField(choices=["csv", "xlsx", "pdf"], default="csv")
