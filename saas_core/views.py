from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from .api_views import CommissionViewSet
from .actions import settle_commission
from .api import IsCompanyMember


class CommissionActionViewSet(CommissionViewSet):
    """
    Extends commission viewset with a settle action.
    """

    @action(detail=True, methods=["post"], permission_classes=[IsCompanyMember])
    def settle(self, request, pk=None):
        commission = self.get_object()
        settle_commission(commission)
        serializer = self.get_serializer(commission)
        return Response(serializer.data, status=status.HTTP_200_OK)
