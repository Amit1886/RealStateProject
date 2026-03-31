from __future__ import annotations

from django.db.models import Q
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.models import SaaSRole

from .models import ReferralEvent, Reward, RewardCoin, RewardRule, RewardTransaction, ScratchCard, SpinHistory, SpinRewardOption
from .serializers import (
    CoinConversionSerializer,
    ReferralEventSerializer,
    RewardCoinSerializer,
    RewardRuleSerializer,
    RewardSerializer,
    RewardTransactionSerializer,
    ScratchCardSerializer,
    SpinHistorySerializer,
    SpinRewardOptionSerializer,
)
from .services import (
    award_daily_login_reward,
    build_referral_share_context,
    claim_scratch_card,
    convert_coins_to_wallet,
    get_or_create_reward_coin,
    process_referral_for_user,
    reveal_scratch_card,
    spin_wheel,
)


def _is_reward_admin(user) -> bool:
    return user.is_superuser or getattr(user, "role", "") in {
        SaaSRole.SUPER_ADMIN,
        SaaSRole.STATE_ADMIN,
        SaaSRole.DISTRICT_ADMIN,
    }


class RewardViewSet(viewsets.ModelViewSet):
    queryset = Reward.objects.select_related("agent")
    serializer_class = RewardSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        if _is_reward_admin(self.request.user):
            return queryset
        return queryset.filter(agent__user=self.request.user)


class RewardCoinViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RewardCoin.objects.select_related("user")
    serializer_class = RewardCoinSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if _is_reward_admin(self.request.user):
            return self.queryset
        return self.queryset.filter(user=self.request.user)

    @action(detail=False, methods=["get"])
    def mine(self, request):
        account = get_or_create_reward_coin(request.user)
        return Response(RewardCoinSerializer(account, context={"request": request}).data)

    @action(detail=False, methods=["post"])
    def convert(self, request):
        serializer = CoinConversionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            reward_txn, wallet_txn = convert_coins_to_wallet(request.user, serializer.validated_data["coins"])
        except ValueError as exc:
            raise serializers.ValidationError({"coins": str(exc)})
        return Response(
            {
                "reward_transaction": RewardTransactionSerializer(reward_txn, context={"request": request}).data,
                "wallet_reference": str(wallet_txn.reference_id),
            }
        )

    @action(detail=False, methods=["post"])
    def claim_daily_login(self, request):
        result = award_daily_login_reward(request.user)
        return Response(
            {
                "claimed": bool(result),
                "coin_account": RewardCoinSerializer(get_or_create_reward_coin(request.user), context={"request": request}).data,
            }
        )

    @action(detail=False, methods=["post"])
    def spin(self, request):
        try:
            spin = spin_wheel(request.user)
        except ValueError as exc:
            raise serializers.ValidationError({"detail": str(exc)})
        return Response(SpinHistorySerializer(spin, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def share_links(self, request):
        payload = build_referral_share_context(request.user, base_url=request.build_absolute_uri("/").rstrip("/"))
        return Response(payload)


class RewardTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RewardTransaction.objects.select_related("coin_account", "user")
    serializer_class = RewardTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if _is_reward_admin(self.request.user):
            return self.queryset
        return self.queryset.filter(user=self.request.user)


class RewardRuleViewSet(viewsets.ModelViewSet):
    queryset = RewardRule.objects.all()
    serializer_class = RewardRuleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]


class ReferralEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ReferralEvent.objects.select_related("referrer", "referred_user", "referrer_reward", "invitee_reward")
    serializer_class = ReferralEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if _is_reward_admin(self.request.user):
            return self.queryset
        return self.queryset.filter(Q(referrer=self.request.user) | Q(referred_user=self.request.user))

    @action(detail=False, methods=["post"])
    def process_mine(self, request):
        result = process_referral_for_user(request.user)
        serializer = ReferralEventSerializer(result, context={"request": request}) if result else None
        return Response(serializer.data if serializer else {"processed": False})


class ScratchCardViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ScratchCard.objects.select_related("user", "reward_transaction")
    serializer_class = ScratchCardSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if _is_reward_admin(self.request.user):
            return self.queryset
        return self.queryset.filter(user=self.request.user)

    @action(detail=True, methods=["post"])
    def reveal(self, request, pk=None):
        card = self.get_object()
        try:
            reveal_scratch_card(request.user, card)
        except ValueError as exc:
            raise serializers.ValidationError({"detail": str(exc)})
        return Response(ScratchCardSerializer(card, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def claim(self, request, pk=None):
        card = self.get_object()
        try:
            claim_scratch_card(request.user, card)
        except ValueError as exc:
            raise serializers.ValidationError({"detail": str(exc)})
        return Response(ScratchCardSerializer(card, context={"request": request}).data)


class SpinRewardOptionViewSet(viewsets.ModelViewSet):
    queryset = SpinRewardOption.objects.all()
    serializer_class = SpinRewardOptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]


class SpinHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SpinHistory.objects.select_related("user", "option", "reward_transaction")
    serializer_class = SpinHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if _is_reward_admin(self.request.user):
            return self.queryset
        return self.queryset.filter(user=self.request.user)
