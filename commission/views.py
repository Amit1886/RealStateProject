from rest_framework import permissions, viewsets

from .models import CommissionPayout, CommissionRule
from .serializers import CommissionPayoutSerializer, CommissionRuleSerializer


class CommissionRuleViewSet(viewsets.ModelViewSet):
    queryset = CommissionRule.objects.all()
    serializer_class = CommissionRuleSerializer
    permission_classes = [permissions.IsAuthenticated]


class CommissionPayoutViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CommissionPayout.objects.select_related("order", "rule").all()
    serializer_class = CommissionPayoutSerializer
    permission_classes = [permissions.IsAuthenticated]
