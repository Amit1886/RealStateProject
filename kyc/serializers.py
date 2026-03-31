from rest_framework import serializers

from .models import KYCDocument, KYCProfile


class KYCDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYCDocument
        fields = "__all__"


class KYCProfileSerializer(serializers.ModelSerializer):
    documents = KYCDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = KYCProfile
        fields = "__all__"

