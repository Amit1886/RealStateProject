from rest_framework import serializers

from .models import Deal, Payment


class PaymentSerializer(serializers.ModelSerializer):
    approved_by_email = serializers.EmailField(source="approved_by.email", read_only=True)
    agent_name = serializers.CharField(source="agent.name", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "company",
            "deal",
            "lead",
            "customer",
            "agent",
            "agent_name",
            "payment_type",
            "direction",
            "amount",
            "adjusted_amount",
            "adjustment_note",
            "adjustment_history",
            "status",
            "reference",
            "approved_by",
            "approved_by_email",
            "approved_at",
            "paid_at",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["approved_at", "paid_at", "created_at", "updated_at"]


class DealSerializer(serializers.ModelSerializer):
    lead_name = serializers.CharField(source="lead.name", read_only=True)
    agent_name = serializers.CharField(source="agent.name", read_only=True)
    property_title = serializers.CharField(source="property.title", read_only=True)
    customer_name = serializers.CharField(source="customer.user.get_full_name", read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta:
        model = Deal
        fields = [
            "id",
            "company",
            "lead",
            "lead_name",
            "customer",
            "customer_name",
            "property",
            "property_title",
            "agent",
            "agent_name",
            "deal_amount",
            "commission_rate",
            "company_share_percent",
            "agent_share_percent",
            "commission_amount",
            "status",
            "stage",
            "closing_date",
            "metadata",
            "payments",
            "closed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["closed_at", "created_at", "updated_at"]
