from django.urls import include, path
from rest_framework.routers import DefaultRouter

from intelligence.views import (
    AggregatedPropertyViewSet,
    DemandHeatmapSnapshotViewSet,
    IntelligenceDashboardAPIView,
    InvestorMatchViewSet,
    InvestorProfileViewSet,
    LeadPurchaseViewSet,
    ManualAggregationAPIView,
    PremiumLeadListingViewSet,
    PriceTrendSnapshotViewSet,
    PropertyAlertSubscriptionViewSet,
    PropertyImportBatchViewSet,
    RealEstateDocumentViewSet,
)

router = DefaultRouter()
router.register("import-batches", PropertyImportBatchViewSet, basename="intelligence-import-batches")
router.register("aggregated-properties", AggregatedPropertyViewSet, basename="intelligence-aggregated-properties")
router.register("heatmaps", DemandHeatmapSnapshotViewSet, basename="intelligence-heatmaps")
router.register("price-trends", PriceTrendSnapshotViewSet, basename="intelligence-price-trends")
router.register("investors", InvestorProfileViewSet, basename="intelligence-investors")
router.register("investor-matches", InvestorMatchViewSet, basename="intelligence-investor-matches")
router.register("alerts", PropertyAlertSubscriptionViewSet, basename="intelligence-alerts")
router.register("premium-leads", PremiumLeadListingViewSet, basename="intelligence-premium-leads")
router.register("lead-purchases", LeadPurchaseViewSet, basename="intelligence-lead-purchases")
router.register("documents", RealEstateDocumentViewSet, basename="intelligence-documents")

urlpatterns = [
    path("aggregate/import/", ManualAggregationAPIView.as_view(), name="intelligence-manual-aggregation"),
    path("dashboard/", IntelligenceDashboardAPIView.as_view(), name="intelligence-dashboard"),
    path("", include(router.urls)),
]
