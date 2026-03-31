from django.db import models
from rest_framework import permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Bank, LoanApplication, LoanProduct
from .serializers import (
    BankSerializer,
    LoanApplicationSerializer,
    LoanCalculatorSerializer,
    LoanEligibilitySerializer,
    LoanProductSerializer,
)
from .services import build_application_snapshot, calculate_emi


class _AdminWriteOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return bool(request.user and request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser))


class BankViewSet(viewsets.ModelViewSet):
    serializer_class = BankSerializer
    permission_classes = [_AdminWriteOrReadOnly]
    queryset = Bank.objects.all()

    def get_queryset(self):
        qs = Bank.objects.all()
        company = getattr(self.request.user, "company", None)
        if not self.request.user.is_superuser:
            qs = qs.filter(models.Q(company=company) | models.Q(company__isnull=True))
        return qs.order_by("name")

    def perform_create(self, serializer):
        serializer.save(company=getattr(self.request.user, "company", None))


class LoanProductViewSet(viewsets.ModelViewSet):
    serializer_class = LoanProductSerializer
    permission_classes = [_AdminWriteOrReadOnly]
    queryset = LoanProduct.objects.select_related("bank")

    def get_queryset(self):
        qs = super().get_queryset()
        company = getattr(self.request.user, "company", None)
        if not self.request.user.is_superuser:
            qs = qs.filter(models.Q(company=company) | models.Q(company__isnull=True))
        if property_type := self.request.query_params.get("property_type"):
            qs = qs.filter(property_type=property_type)
        if bank := self.request.query_params.get("bank"):
            qs = qs.filter(bank_id=bank)
        return qs.filter(active=True) if self.request.method == "GET" else qs

    def perform_create(self, serializer):
        serializer.save(company=getattr(self.request.user, "company", None))


class LoanApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = LoanApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = LoanApplication.objects.select_related("applicant", "property", "loan_product", "loan_product__bank")

    def get_queryset(self):
        qs = super().get_queryset()
        company = getattr(self.request.user, "company", None)
        user = self.request.user
        if user.is_superuser or user.is_staff:
            return qs.filter(models.Q(company=company) | models.Q(company__isnull=True))
        return qs.filter(applicant=user)

    def perform_create(self, serializer):
        serializer.save(
            applicant=self.request.user,
            company=getattr(self.request.user, "company", None),
        )


class LoanCalculatorAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = LoanCalculatorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        return Response(
            {
                "emi": calculate_emi(
                    data["principal"],
                    data["annual_rate"],
                    data["tenure_years"],
                )
            }
        )


class LoanEligibilityAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = LoanEligibilitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        return Response(build_application_snapshot(**data))

