from django.db import models
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from communication.models import EmailLog, MessageLog, SMSLog
from communication.serializers import EmailLogSerializer, MessageLogSerializer, SMSLogSerializer
from communication.services import queue_notification_event


class _CompanyScopedViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def _company(self):
        return getattr(self.request.user, "company", None)


class MessageLogViewSet(_CompanyScopedViewSet):
    queryset = MessageLog.objects.select_related("sender", "receiver", "lead")
    serializer_class = MessageLogSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or getattr(user, "is_staff", False):
            return qs
        company = self._company()
        return qs.filter(
            models.Q(company=company, company__isnull=False)
            | models.Q(sender=user)
            | models.Q(receiver=user)
        )

    def perform_create(self, serializer):
        serializer.save(company=self._company(), sender=serializer.validated_data.get("sender") or self.request.user)


class EmailLogViewSet(_CompanyScopedViewSet):
    queryset = EmailLog.objects.all()
    serializer_class = EmailLogSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or getattr(user, "is_staff", False):
            return qs
        return qs.filter(company=self._company())

    def perform_create(self, serializer):
        serializer.save(company=self._company())


class SMSLogViewSet(_CompanyScopedViewSet):
    queryset = SMSLog.objects.all()
    serializer_class = SMSLogSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or getattr(user, "is_staff", False):
            return qs
        return qs.filter(company=self._company())

    def perform_create(self, serializer):
        serializer.save(company=self._company())


class CommunicationEventAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        users = []
        if request.user.is_authenticated:
            users.append(request.user)
        created = queue_notification_event(
            users=users,
            title=str(request.data.get("title") or "Notification"),
            body=str(request.data.get("body") or ""),
            channels=request.data.get("channels") or ["in_app"],
            phone=str(request.data.get("phone") or ""),
            email=str(request.data.get("email") or ""),
            whatsapp_number=str(request.data.get("whatsapp_number") or ""),
            sender=request.user,
            metadata=request.data.get("metadata") or {},
        )
        return Response({"detail": "queued", "created": created}, status=status.HTTP_202_ACCEPTED)
