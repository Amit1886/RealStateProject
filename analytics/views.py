from rest_framework import permissions, viewsets

from .models import CreditRiskScore, ProductVelocity, SalesAnalyticsSnapshot, SalesmanPerformance
from .serializers import (
    CreditRiskScoreSerializer,
    ProductVelocitySerializer,
    SalesAnalyticsSnapshotSerializer,
    SalesmanPerformanceSerializer,
)


class SalesAnalyticsSnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SalesAnalyticsSnapshot.objects.all()
    serializer_class = SalesAnalyticsSnapshotSerializer
    permission_classes = [permissions.IsAuthenticated]


class ProductVelocityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProductVelocity.objects.select_related("product").all()
    serializer_class = ProductVelocitySerializer
    permission_classes = [permissions.IsAuthenticated]


class SalesmanPerformanceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SalesmanPerformance.objects.select_related("user").all()
    serializer_class = SalesmanPerformanceSerializer
    permission_classes = [permissions.IsAuthenticated]


class CreditRiskScoreViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CreditRiskScore.objects.select_related("user").all()
    serializer_class = CreditRiskScoreSerializer
    permission_classes = [permissions.IsAuthenticated]
