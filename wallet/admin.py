from django.contrib import admin

from wallet.models import Wallet, WalletAccount, WalletAuditLog, WalletLedger, WalletTransaction, WalletTransfer, WithdrawRequest


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("id", "wallet_code", "user", "balance", "locked_balance", "currency", "status", "updated_at")
    list_filter = ("status", "currency")
    search_fields = ("user__email", "wallet_code")
    readonly_fields = ("wallet_uuid", "created_at", "updated_at")


@admin.register(WalletAccount)
class WalletAccountAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "account_type", "label", "is_default", "status", "updated_at")
    list_filter = ("account_type", "status", "is_default")
    search_fields = ("user__email", "upi_id", "account_number", "label")


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "reference_id", "wallet", "entry_type", "source", "status", "amount", "created_at")
    list_filter = ("entry_type", "source", "status")
    search_fields = ("wallet__user__email", "reference", "idempotency_key")
    readonly_fields = ("reference_id", "created_at", "processed_at")


@admin.register(WalletLedger)
class WalletLedgerAdmin(admin.ModelAdmin):
    list_display = ("id", "wallet", "transaction", "balance_before", "balance_after", "created_at")
    search_fields = ("wallet__user__email", "transaction__reference")
    readonly_fields = ("created_at",)


@admin.register(WalletTransfer)
class WalletTransferAdmin(admin.ModelAdmin):
    list_display = ("id", "reference_id", "sender_wallet", "receiver_wallet", "amount", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("reference_id", "sender_wallet__user__email", "receiver_wallet__user__email")
    readonly_fields = ("reference_id", "processed_at", "created_at")


@admin.register(WithdrawRequest)
class WithdrawRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "reference_id", "wallet", "user", "amount", "status", "requested_at", "processed_at")
    list_filter = ("status",)
    search_fields = ("wallet__user__email", "payout_reference")
    readonly_fields = ("reference_id", "requested_at", "approved_at", "processed_at")


@admin.register(WalletAuditLog)
class WalletAuditLogAdmin(admin.ModelAdmin):
    list_display = ("id", "wallet", "transaction", "actor", "action", "created_at")
    list_filter = ("action",)
    search_fields = ("wallet__user__email", "action")
    readonly_fields = ("created_at",)
