from django.urls import path
from rest_framework.routers import DefaultRouter

from saas_core.api_views import (
    LeadViewSet,
    AgentViewSet,
    DealViewSet,
    WalletViewSet,
    WalletTransactionViewSet,
    PropertyViewSet,
    BuilderViewSet,
    PropertyProjectViewSet,
)
from saas_core.reports import SummaryReportView
from saas_core.views import CommissionActionViewSet

router = DefaultRouter()
router.register(r"leads", LeadViewSet, basename="lead")
router.register(r"agents", AgentViewSet, basename="agent")
router.register(r"deals", DealViewSet, basename="deal")
router.register(r"properties", PropertyViewSet, basename="property")
router.register(r"builders", BuilderViewSet, basename="builder")
router.register(r"projects", PropertyProjectViewSet, basename="property-project")
router.register(r"wallet", WalletViewSet, basename="wallet")
router.register(r"wallet-transactions", WalletTransactionViewSet, basename="wallet-transaction")
router.register(r"commissions", CommissionActionViewSet, basename="commission")

urlpatterns = router.urls + [
    path("reports/summary/", SummaryReportView.as_view(), name="summary-report"),
]
