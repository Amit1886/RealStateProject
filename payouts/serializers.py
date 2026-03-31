from rest_framework import serializers

from .models import Payout


class PayoutSerializer(serializers.ModelSerializer):
    agent_name = serializers.CharField(source="agent.name", read_only=True)
    lead_name = serializers.CharField(source="lead.name", read_only=True)

    class Meta:
        model = Payout
        fields = [
            "id",
            "agent",
            "agent_name",
            "lead",
            "lead_name",
            "amount",
            "currency",
            "status",
            "approval_notes",
            "metadata",
            "generated_by",
            "approved_by",
            "generated_at",
            "approved_at",
            "paid_at",
        ]
        read_only_fields = ["generated_at", "approved_at", "paid_at"]

