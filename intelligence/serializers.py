from rest_framework import serializers

from intelligence.models import (
    AggregatedProperty,
    DemandHeatmapSnapshot,
    InvestorMatch,
    InvestorProfile,
    LeadPurchase,
    PremiumLeadListing,
    PriceTrendSnapshot,
    PropertyAlertSubscription,
    PropertyImportBatch,
    RealEstateDocument,
)


class PropertyImportBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyImportBatch
        fields = "__all__"
        read_only_fields = ["started_at", "completed_at", "fetched_count", "inserted_count", "duplicate_count", "normalized_count", "last_error", "created_at", "updated_at"]


class AggregatedPropertySerializer(serializers.ModelSerializer):
    matched_property_title = serializers.CharField(source="matched_property.title", read_only=True)

    class Meta:
        model = AggregatedProperty
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]


class DemandHeatmapSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = DemandHeatmapSnapshot
        fields = "__all__"


class PriceTrendSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceTrendSnapshot
        fields = "__all__"


class InvestorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvestorProfile
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]


class InvestorMatchSerializer(serializers.ModelSerializer):
    property_title = serializers.CharField(source="property.title", read_only=True)
    project_title = serializers.CharField(source="project.title", read_only=True)

    class Meta:
        model = InvestorMatch
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "notified_at"]


class PropertyAlertSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyAlertSubscription
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]


class PremiumLeadListingSerializer(serializers.ModelSerializer):
    lead_name = serializers.CharField(source="lead.name", read_only=True)
    buyer_agent_name = serializers.CharField(source="buyer_agent.name", read_only=True)

    class Meta:
        model = PremiumLeadListing
        fields = "__all__"
        read_only_fields = ["buyer_agent", "created_at", "updated_at"]


class LeadPurchaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadPurchase
        fields = "__all__"
        read_only_fields = ["purchased_at"]


class RealEstateDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RealEstateDocument
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "uploaded_by"]
