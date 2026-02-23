from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CreditRiskScoreViewSet, ProductVelocityViewSet, SalesAnalyticsSnapshotViewSet, SalesmanPerformanceViewSet

router = DefaultRouter()
router.register("snapshots", SalesAnalyticsSnapshotViewSet, basename="analytics-snapshot")
router.register("product-velocity", ProductVelocityViewSet, basename="analytics-product-velocity")
router.register("salesman-performance", SalesmanPerformanceViewSet, basename="analytics-salesman")
router.register("credit-risk", CreditRiskScoreViewSet, basename="analytics-credit-risk")

urlpatterns = [path("", include(router.urls))]
