from rest_framework import serializers

from .models import PropertyVerification, VerificationDocument


class VerificationDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerificationDocument
        fields = [
            "id",
            "verification",
            "document_type",
            "file",
            "external_url",
            "title",
            "uploaded_by",
            "created_at",
        ]
        read_only_fields = ["uploaded_by", "created_at"]


class PropertyVerificationSerializer(serializers.ModelSerializer):
    documents = VerificationDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = PropertyVerification
        fields = [
            "id",
            "property",
            "requested_by",
            "reviewed_by",
            "status",
            "notes",
            "reviewed_at",
            "created_at",
            "documents",
        ]
        read_only_fields = ["requested_by", "reviewed_by", "reviewed_at", "created_at"]

