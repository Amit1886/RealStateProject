from django.db import models
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import PropertyVerification, VerificationDocument
from .serializers import PropertyVerificationSerializer, VerificationDocumentSerializer


class _AdminWriteOrUserCreate(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        if view.action == "create":
            return bool(request.user and request.user.is_authenticated)
        return bool(request.user and request.user.is_authenticated and (request.user.is_superuser or request.user.is_staff))


class PropertyVerificationViewSet(viewsets.ModelViewSet):
    serializer_class = PropertyVerificationSerializer
    permission_classes = [_AdminWriteOrUserCreate]
    queryset = PropertyVerification.objects.select_related("property", "requested_by", "reviewed_by")

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        company = getattr(user, "company", None)
        if user.is_superuser or user.is_staff:
            return qs.filter(models.Q(company=company) | models.Q(company__isnull=True))
        return qs.filter(models.Q(requested_by=user) | models.Q(property__owner=user) | models.Q(property__assigned_agent__user=user))

    def perform_create(self, serializer):
        serializer.save(
            requested_by=self.request.user,
            company=getattr(self.request.user, "company", None),
        )

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        verification = self.get_object()
        verification.mark_reviewed(reviewer=request.user, status=PropertyVerification.Status.APPROVED, notes=str(request.data.get("notes") or ""))
        return Response(self.get_serializer(verification).data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
    def reject(self, request, pk=None):
        verification = self.get_object()
        verification.mark_reviewed(reviewer=request.user, status=PropertyVerification.Status.REJECTED, notes=str(request.data.get("notes") or ""))
        return Response(self.get_serializer(verification).data)


class VerificationDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = VerificationDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = VerificationDocument.objects.select_related("verification", "uploaded_by")

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or user.is_staff:
            return qs
        return qs.filter(
            models.Q(uploaded_by=user)
            | models.Q(verification__requested_by=user)
            | models.Q(verification__property__owner=user)
        )

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)

