from django.db import models
from rest_framework import permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from leads.models import Property

from .models import Scheme, UserSchemeMatch
from .serializers import SchemeMatcherSerializer, SchemeSerializer, UserSchemeMatchSerializer
from .services import create_scheme_matches


class _AdminWriteOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return bool(request.user and request.user.is_authenticated and (request.user.is_superuser or request.user.is_staff))


class SchemeViewSet(viewsets.ModelViewSet):
    serializer_class = SchemeSerializer
    permission_classes = [_AdminWriteOrReadOnly]
    queryset = Scheme.objects.all()

    def get_queryset(self):
        qs = Scheme.objects.all()
        company = getattr(self.request.user, "company", None)
        if not self.request.user.is_superuser:
            qs = qs.filter(models.Q(company=company) | models.Q(company__isnull=True))
        if state := self.request.query_params.get("state"):
            qs = qs.filter(state__iexact=state)
        return qs

    def perform_create(self, serializer):
        serializer.save(company=getattr(self.request.user, "company", None))


class UserSchemeMatchViewSet(viewsets.ModelViewSet):
    serializer_class = UserSchemeMatchSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = UserSchemeMatch.objects.select_related("scheme", "property", "user")

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or user.is_staff:
            company = getattr(user, "company", None)
            return qs.filter(models.Q(company=company) | models.Q(company__isnull=True))
        return qs.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, company=getattr(self.request.user, "company", None))


class SchemeMatcherAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = SchemeMatcherSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        property_obj = None
        if data.get("property_id"):
            property_obj = Property.objects.filter(id=data["property_id"]).first()
        matches = create_scheme_matches(
            user=request.user,
            income=data["income"],
            location=data["location"],
            ownership_status=data["ownership_status"],
            property_obj=property_obj,
            company=getattr(request.user, "company", None),
        )
        return Response(UserSchemeMatchSerializer(matches, many=True).data)

