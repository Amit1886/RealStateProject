from django.urls import include, path
from rest_framework.routers import DefaultRouter

from wallet.views import (
    WalletAccountViewSet,
    WalletAuditLogViewSet,
    WalletLedgerViewSet,
    WalletTransactionViewSet,
    WalletTransferViewSet,
    WalletViewSet,
    WithdrawRequestViewSet,
)

router = DefaultRouter()
router.register("wallets", WalletViewSet, basename="wallets")
router.register("accounts", WalletAccountViewSet, basename="wallet-accounts")
router.register("transactions", WalletTransactionViewSet, basename="wallet-transactions")
router.register("ledger", WalletLedgerViewSet, basename="wallet-ledger")
router.register("transfers", WalletTransferViewSet, basename="wallet-transfers")
router.register("withdraw-requests", WithdrawRequestViewSet, basename="wallet-withdraw-requests")
router.register("audit-logs", WalletAuditLogViewSet, basename="wallet-audit-logs")

urlpatterns = [
    path("balance/", WalletViewSet.as_view({"get": "balance"}), name="wallet-balance"),
    path("summary/", WalletViewSet.as_view({"get": "summary"}), name="wallet-summary"),
    path("statement/", WalletViewSet.as_view({"get": "statement"}), name="wallet-statement"),
    path("", include(router.urls)),
]
