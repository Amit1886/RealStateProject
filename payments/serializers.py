from rest_framework import serializers

from .models import DailyCashSummary, PaymentTransaction


class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = "__all__"


class DailyCashSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyCashSummary
        fields = "__all__"
