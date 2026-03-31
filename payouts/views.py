from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.models import SaaSRole
from .models import Payout
from .serializers import PayoutSerializer
from agents.wallet import AgentWallet


class PayoutViewSet(viewsets.ModelViewSet):
    queryset = Payout.objects.select_related("agent", "lead")
    serializer_class = PayoutSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or getattr(user, "role", "") in {
            SaaSRole.SUPER_ADMIN,
            SaaSRole.STATE_ADMIN,
            SaaSRole.DISTRICT_ADMIN,
        }:
            return qs
        return qs.filter(agent__user=user)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def approve(self, request, pk=None):
        payout = self.get_object()
        payout.approve(user=request.user, notes=request.data.get("notes", ""))
        return Response(self.get_serializer(payout).data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def mark_paid(self, request, pk=None):
        payout = self.get_object()
        payout.mark_paid(user=request.user, external_ref=request.data.get("external_ref"))
        # Release locked funds if any
        try:
            wallet = AgentWallet.objects.get(agent=payout.agent)
            wallet.release_locked(payout.amount)
        except AgentWallet.DoesNotExist:
            pass
        return Response(self.get_serializer(payout).data)
