from rest_framework import filters, permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CommissionLedger, UserProfileExt, WalletLedger
from .serializers import CommissionLedgerSerializer, CurrentUserSerializer, UserProfileExtSerializer, WalletLedgerSerializer


class CurrentUserAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(CurrentUserSerializer(request.user, context={"request": request}).data)


class UserProfileExtViewSet(viewsets.ModelViewSet):
    queryset = UserProfileExt.objects.select_related("user").all()
    serializer_class = UserProfileExtSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["user__email", "user__username", "role"]
    ordering_fields = ["created_at", "updated_at", "role"]


class WalletLedgerViewSet(viewsets.ModelViewSet):
    queryset = WalletLedger.objects.select_related("user").all()
    serializer_class = WalletLedgerSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["reference", "source", "user__email"]
    ordering_fields = ["created_at", "amount"]


class CommissionLedgerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CommissionLedger.objects.select_related("user").all()
    serializer_class = CommissionLedgerSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["order_id", "role", "user__email"]
    ordering_fields = ["created_at", "commission_amount", "margin"]
