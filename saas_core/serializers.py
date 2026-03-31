from rest_framework import serializers
from leads.models import Lead
from agents.models import Agent
from deals.models import Deal
from wallet.models import Wallet, WalletTransaction
from deals.models_commission import Commission
from leads.serializers import PropertySerializer, BuilderSerializer, PropertyProjectSerializer


class LeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = [
            "id",
            "name",
            "mobile",
            "email",
            "status",
            "stage",
            "temperature",
            "budget",
            "property_type",
            "preferred_location",
            "assigned_agent",
            "lead_score",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("created_at", "updated_at")


class AgentSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Agent
        fields = [
            "id",
            "user",
            "user_email",
            "name",
            "phone",
            "specialization",
            "kyc_verified",
            "rating",
            "total_sales",
            "total_visits",
            "is_active",
        ]
        read_only_fields = ("rating", "total_sales", "total_visits")


class DealSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deal
        fields = [
            "id",
            "lead",
            "agent",
            "deal_amount",
            "commission_amount",
            "status",
            "closed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("created_at", "updated_at")


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ["id", "balance", "currency", "updated_at", "created_at"]
        read_only_fields = fields


class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = ["id", "entry_type", "amount", "source", "reference", "metadata", "created_at"]
        read_only_fields = ("created_at",)


class CommissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Commission
        fields = [
            "id",
            "deal",
            "admin_amount",
            "agent_amount",
            "sub_agent_amount",
            "total_amount",
            "settled",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("created_at", "updated_at", "total_amount")
