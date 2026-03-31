from rest_framework import serializers

from .models import DailyCashSummary, PaymentOrder, PaymentTransaction


class PaymentOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentOrder
        fields = "__all__"
        read_only_fields = ("reference_id", "provider_order_id", "provider_payment_id", "signature", "paid_at", "failed_at", "created_at", "updated_at")


class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = "__all__"
        read_only_fields = ("reference_id", "created_at", "updated_at", "processed_at")


class DailyCashSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyCashSummary
        fields = "__all__"
