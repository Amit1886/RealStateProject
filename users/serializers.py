from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import CommissionLedger, UserProfileExt, WalletLedger


User = get_user_model()


class UserBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "username", "mobile"]


class CurrentUserSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)
    company_domain = serializers.CharField(source="company.domain", read_only=True)
    agent_profile_id = serializers.IntegerField(source="agent_profile.id", read_only=True)
    customer_profile_id = serializers.IntegerField(source="customer_profile.id", read_only=True)
    wallet_balance = serializers.DecimalField(
        source="wallet.balance",
        max_digits=14,
        decimal_places=2,
        read_only=True,
        default="0.00",
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "mobile",
            "role",
            "company",
            "company_name",
            "company_domain",
            "is_staff",
            "is_superuser",
            "agent_profile_id",
            "customer_profile_id",
            "wallet_balance",
        ]


class UserProfileExtSerializer(serializers.ModelSerializer):
    user = UserBriefSerializer(read_only=True)

    class Meta:
        model = UserProfileExt
        fields = "__all__"


class WalletLedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletLedger
        fields = "__all__"


class CommissionLedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommissionLedger
        fields = "__all__"
