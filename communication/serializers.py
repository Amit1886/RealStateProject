from rest_framework import serializers

from communication.models import EmailLog, MessageLog, SMSLog


class MessageLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageLog
        fields = [
            "id",
            "company",
            "sender",
            "receiver",
            "lead",
            "message_type",
            "message",
            "status",
            "provider",
            "provider_ref",
            "metadata",
            "delivered_at",
            "created_at",
        ]
        read_only_fields = ["delivered_at", "created_at"]


class EmailLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailLog
        fields = [
            "id",
            "company",
            "sender",
            "recipient",
            "subject",
            "body",
            "status",
            "provider",
            "provider_ref",
            "metadata",
            "sent_at",
            "created_at",
        ]
        read_only_fields = ["sent_at", "created_at"]


class SMSLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SMSLog
        fields = [
            "id",
            "company",
            "phone",
            "message",
            "status",
            "provider",
            "provider_ref",
            "metadata",
            "sent_at",
            "created_at",
        ]
        read_only_fields = ["sent_at", "created_at"]
