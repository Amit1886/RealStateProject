from rest_framework import serializers

from .models import ReferralEvent, Reward, RewardCoin, RewardRule, RewardTransaction, ScratchCard, SpinHistory, SpinRewardOption


class RewardSerializer(serializers.ModelSerializer):
    agent_name = serializers.CharField(source="agent.name", read_only=True)

    class Meta:
        model = Reward
        fields = [
            "id",
            "agent",
            "agent_name",
            "title",
            "type",
            "condition",
            "achieved",
            "achieved_at",
            "metadata",
            "certificate_file",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["achieved_at", "created_at", "updated_at"]


class RewardCoinSerializer(serializers.ModelSerializer):
    class Meta:
        model = RewardCoin
        fields = [
            "id",
            "user",
            "balance",
            "lifetime_earned",
            "lifetime_redeemed",
            "available_spins",
            "available_scratch_cards",
            "last_daily_login_at",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class RewardRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RewardRule
        fields = "__all__"


class RewardTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RewardTransaction
        fields = "__all__"
        read_only_fields = ["reference_id", "created_at"]


class ReferralEventSerializer(serializers.ModelSerializer):
    referrer_email = serializers.CharField(source="referrer.email", read_only=True)
    referred_user_email = serializers.CharField(source="referred_user.email", read_only=True)

    class Meta:
        model = ReferralEvent
        fields = [
            "id",
            "code_used",
            "referrer",
            "referrer_email",
            "referred_user",
            "referred_user_email",
            "status",
            "referrer_reward",
            "invitee_reward",
            "wallet_reward_reference",
            "metadata",
            "created_at",
            "qualified_at",
            "rewarded_at",
        ]
        read_only_fields = fields


class ScratchCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScratchCard
        fields = "__all__"
        read_only_fields = ["reference_id", "revealed_at", "claimed_at", "created_at"]


class SpinRewardOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpinRewardOption
        fields = "__all__"


class SpinHistorySerializer(serializers.ModelSerializer):
    option_label = serializers.CharField(source="option.label", read_only=True)

    class Meta:
        model = SpinHistory
        fields = "__all__"
        read_only_fields = ["reference_id", "created_at", "option_label"]


class CoinConversionSerializer(serializers.Serializer):
    coins = serializers.IntegerField(min_value=1)


class ScratchActionSerializer(serializers.Serializer):
    card_id = serializers.IntegerField()
