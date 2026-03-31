from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BankViewSet,
    LoanApplicationViewSet,
    LoanCalculatorAPIView,
    LoanEligibilityAPIView,
    LoanProductViewSet,
)

router = DefaultRouter()
router.register("banks", BankViewSet, basename="loan-banks")
router.register("products", LoanProductViewSet, basename="loan-products")
router.register("applications", LoanApplicationViewSet, basename="loan-applications")

urlpatterns = [
    path("calculator/", LoanCalculatorAPIView.as_view(), name="loan-calculator"),
    path("eligibility/", LoanEligibilityAPIView.as_view(), name="loan-eligibility"),
    path("", include(router.urls)),
]

