from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AIQueryLogViewSet,
    CreditRiskInternalAPIView,
    CustomerRiskScoreViewSet,
    DemandForecastViewSet,
    ForecastInternalAPIView,
    ProductDemandForecastViewSet,
    SalesmanScoreInternalAPIView,
    SalesmanScoreViewSet,
)

router = DefaultRouter()
router.register("queries", AIQueryLogViewSet, basename="ai-query")
router.register("forecasts", DemandForecastViewSet, basename="ai-forecast")
router.register("forecast-records", ProductDemandForecastViewSet, basename="ai-forecast-record")
router.register("credit-risk-scores", CustomerRiskScoreViewSet, basename="ai-credit-risk-score")
router.register("salesman-scores", SalesmanScoreViewSet, basename="ai-salesman-score")

urlpatterns = [
    path("forecast/", ForecastInternalAPIView.as_view(), name="forecast-internal"),
    path("credit-risk/", CreditRiskInternalAPIView.as_view(), name="credit-risk-internal"),
    path("salesman-score/", SalesmanScoreInternalAPIView.as_view(), name="salesman-score-internal"),
    path("", include(router.urls)),
]
