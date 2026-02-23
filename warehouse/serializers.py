from rest_framework import serializers

from .models import Warehouse, WarehouseStaffAssignment


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = "__all__"


class WarehouseStaffAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = WarehouseStaffAssignment
        fields = "__all__"
