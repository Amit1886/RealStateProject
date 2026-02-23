from rest_framework import permissions, viewsets

from .models import DeliveryAssignment, DeliveryTrackingPing
from .serializers import DeliveryAssignmentSerializer, DeliveryTrackingPingSerializer


class DeliveryAssignmentViewSet(viewsets.ModelViewSet):
    queryset = DeliveryAssignment.objects.select_related("order", "partner").all()
    serializer_class = DeliveryAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]


class DeliveryTrackingPingViewSet(viewsets.ModelViewSet):
    queryset = DeliveryTrackingPing.objects.select_related("assignment").all()
    serializer_class = DeliveryTrackingPingSerializer
    permission_classes = [permissions.IsAuthenticated]
