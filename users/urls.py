from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CommissionLedgerViewSet, CurrentUserAPIView, UserProfileExtViewSet, WalletLedgerViewSet

router = DefaultRouter()
router.register("profiles", UserProfileExtViewSet, basename="users-profile")
router.register("wallet-ledger", WalletLedgerViewSet, basename="users-wallet")
router.register("commission-ledger", CommissionLedgerViewSet, basename="users-commission")

urlpatterns = [
    path("me/", CurrentUserAPIView.as_view(), name="users-me"),
    path("", include(router.urls)),
]
