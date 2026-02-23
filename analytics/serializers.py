from rest_framework import serializers

from .models import CreditRiskScore, ProductVelocity, SalesAnalyticsSnapshot, SalesmanPerformance


class SalesAnalyticsSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesAnalyticsSnapshot
        fields = "__all__"


class ProductVelocitySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVelocity
        fields = "__all__"


class SalesmanPerformanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesmanPerformance
        fields = "__all__"


class CreditRiskScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditRiskScore
        fields = "__all__"
