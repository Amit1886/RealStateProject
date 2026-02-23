from rest_framework import serializers

from .models import ScanEvent, ScannerConfig


class ScannerConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScannerConfig
        fields = "__all__"


class ScanEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScanEvent
        fields = "__all__"
