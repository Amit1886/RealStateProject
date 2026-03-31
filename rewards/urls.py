from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ReferralEventViewSet,
    RewardCoinViewSet,
    RewardRuleViewSet,
    RewardTransactionViewSet,
    RewardViewSet,
    ScratchCardViewSet,
    SpinHistoryViewSet,
    SpinRewardOptionViewSet,
)

router = DefaultRouter()
router.register("rewards", RewardViewSet, basename="rewards")
router.register("coins", RewardCoinViewSet, basename="reward-coins")
router.register("transactions", RewardTransactionViewSet, basename="reward-transactions")
router.register("rules", RewardRuleViewSet, basename="reward-rules")
router.register("referrals", ReferralEventViewSet, basename="reward-referrals")
router.register("scratch-cards", ScratchCardViewSet, basename="scratch-cards")
router.register("spin-options", SpinRewardOptionViewSet, basename="spin-options")
router.register("spin-history", SpinHistoryViewSet, basename="spin-history")

urlpatterns = [path("", include(router.urls))]
