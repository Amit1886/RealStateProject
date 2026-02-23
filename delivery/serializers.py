from rest_framework import serializers

from .models import DeliveryAssignment, DeliveryTrackingPing


class DeliveryAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryAssignment
        fields = "__all__"


class DeliveryTrackingPingSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryTrackingPing
        fields = "__all__"
