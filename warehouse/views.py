from rest_framework import filters, permissions, viewsets

from .models import Warehouse, WarehouseStaffAssignment
from .serializers import WarehouseSerializer, WarehouseStaffAssignmentSerializer


class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "code", "address"]
    ordering_fields = ["created_at", "name"]


class WarehouseStaffAssignmentViewSet(viewsets.ModelViewSet):
    queryset = WarehouseStaffAssignment.objects.select_related("warehouse", "user").all()
    serializer_class = WarehouseStaffAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["warehouse__name", "user__email"]
    ordering_fields = ["assigned_at"]
