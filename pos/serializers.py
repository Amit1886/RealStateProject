from rest_framework import serializers

from .models import POSHoldBill, POSReprintLog, POSSession, POSTerminal


class POSTerminalSerializer(serializers.ModelSerializer):
    class Meta:
        model = POSTerminal
        fields = "__all__"


class POSSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = POSSession
        fields = "__all__"


class POSHoldBillSerializer(serializers.ModelSerializer):
    class Meta:
        model = POSHoldBill
        fields = "__all__"


class POSReprintLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = POSReprintLog
        fields = "__all__"
