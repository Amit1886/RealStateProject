from rest_framework import serializers

from crm.models import AgentAchievement, AgentScore, CallLog, CustomerNote, CustomerProfile, FollowUp


class CustomerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerProfile
        fields = ["id", "user", "company", "last_contacted_at", "lifecycle_stage", "metadata"]


class CustomerNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerNote
        fields = ["id", "customer", "author", "note", "created_at"]
        read_only_fields = ["created_at"]


class CallLogSerializer(serializers.ModelSerializer):
    lead_name = serializers.CharField(source="lead.name", read_only=True)

    class Meta:
        model = CallLog
        fields = [
            "id",
            "customer",
            "lead",
            "lead_name",
            "agent",
            "direction",
            "phone_number",
            "duration_seconds",
            "outcome",
            "telephony_provider",
            "external_call_id",
            "recording_url",
            "missed_call",
            "note",
            "metadata",
            "created_at",
        ]
        read_only_fields = ["created_at"]


class FollowUpSerializer(serializers.ModelSerializer):
    class Meta:
        model = FollowUp
        fields = ["id", "customer", "owner", "title", "due_at", "completed_at", "created_at"]
        read_only_fields = ["completed_at", "created_at"]


class AgentScoreSerializer(serializers.ModelSerializer):
    agent_name = serializers.CharField(source="agent.name", read_only=True)

    class Meta:
        model = AgentScore
        fields = [
            "id",
            "agent",
            "agent_name",
            "score_date",
            "leads_assigned",
            "leads_closed",
            "response_time_seconds",
            "points",
            "target_points",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class AgentAchievementSerializer(serializers.ModelSerializer):
    agent_name = serializers.CharField(source="agent.name", read_only=True)

    class Meta:
        model = AgentAchievement
        fields = [
            "id",
            "agent",
            "agent_name",
            "code",
            "title",
            "kind",
            "description",
            "points",
            "achieved_at",
            "metadata",
        ]
        read_only_fields = ["achieved_at"]
