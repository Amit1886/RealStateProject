from rest_framework import permissions, viewsets

from .models import RealtimeEvent
from .serializers import RealtimeEventSerializer


class RealtimeEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RealtimeEvent.objects.all()
    serializer_class = RealtimeEventSerializer
    permission_classes = [permissions.IsAuthenticated]
