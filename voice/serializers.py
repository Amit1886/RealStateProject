from rest_framework import serializers

from voice.models import VoiceCall, VoiceCallTurn


class VoiceCallTurnSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoiceCallTurn
        fields = ["id", "call", "speaker", "message", "sequence", "created_at"]
        read_only_fields = ["created_at"]


class VoiceCallSerializer(serializers.ModelSerializer):
    turns = VoiceCallTurnSerializer(many=True, read_only=True)
    lead_name = serializers.CharField(source="lead.name", read_only=True)

    class Meta:
        model = VoiceCall
        fields = [
            "id",
            "lead",
            "lead_name",
            "agent",
            "status",
            "trigger",
            "language",
            "script_prompt",
            "response_text",
            "transcript",
            "summary",
            "structured_response",
            "qualification_status",
            "qualified",
            "recording_url",
            "provider",
            "provider_call_id",
            "last_error",
            "started_at",
            "completed_at",
            "created_at",
            "updated_at",
            "turns",
        ]
        read_only_fields = ["started_at", "completed_at", "created_at", "updated_at"]
