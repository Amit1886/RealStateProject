from rest_framework import serializers

from .models import Agent, AgentCoverageArea, AgentVerification


class AgentCoverageAreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentCoverageArea
        fields = [
            "id",
            "agent",
            "country",
            "state",
            "district",
            "tehsil",
            "village",
            "city",
            "pin_code",
            "is_primary",
            "is_active",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class AgentSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_role = serializers.CharField(source="user.role", read_only=True)
    parent_agent_name = serializers.CharField(source="parent_agent.name", read_only=True)
    wallet_balance = serializers.SerializerMethodField()
    total_earned = serializers.SerializerMethodField()
    coverage_areas = AgentCoverageAreaSerializer(many=True, read_only=True)
    verifications = serializers.SerializerMethodField()

    class Meta:
        model = Agent
        fields = [
            "id",
            "user",
            "user_email",
            "user_role",
            "company",
            "name",
            "phone",
            "license_number",
            "profile_image",
            "address",
            "country",
            "city",
            "district",
            "state",
            "tehsil",
            "village",
            "pin_code",
            "experience_years",
            "specialization",
            "kyc_verified",
            "rating",
            "performance_score",
            "commission_rate",
            "total_sales",
            "total_visits",
            "pincodes",
            "service_areas",
            "parent_agent",
            "parent_agent_name",
            "approval_status",
            "franchise_name",
            "kyc_document",
            "kyc_status",
            "kyc_verified_at",
            "coverage_areas",
            "verifications",
            "is_active",
            "is_blocked",
            "frozen_wallet",
            "current_latitude",
            "current_longitude",
            "assigned_location",
            "current_location",
            "last_ping_at",
            "risk_score",
            "risk_level",
            "performance",
            "last_assigned_at",
            "wallet_balance",
            "total_earned",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["last_assigned_at", "created_at", "updated_at"]

    def get_wallet_balance(self, obj):
        wallet = getattr(obj, "wallet", None)
        return wallet.balance if wallet else 0

    def get_total_earned(self, obj):
        wallet = getattr(obj, "wallet", None)
        return wallet.total_earned if wallet else 0

    def get_verifications(self, obj):
        qs = obj.verifications.order_by("-created_at")[:5]
        return AgentVerificationSerializer(qs, many=True, context=self.context).data


class AgentVerificationSerializer(serializers.ModelSerializer):
    verified_by_email = serializers.EmailField(source="verified_by.email", read_only=True)

    class Meta:
        model = AgentVerification
        fields = [
            "id",
            "agent",
            "document_type",
            "document_file",
            "status",
            "remarks",
            "verified_by",
            "verified_by_email",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["reviewed_at", "created_at", "updated_at"]
