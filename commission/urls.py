from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CommissionPayoutViewSet, CommissionRuleViewSet

router = DefaultRouter()
router.register("rules", CommissionRuleViewSet, basename="commission-rule")
router.register("payouts", CommissionPayoutViewSet, basename="commission-payout")

urlpatterns = [path("", include(router.urls))]
