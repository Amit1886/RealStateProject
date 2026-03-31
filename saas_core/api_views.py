from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from leads.models import Lead, Property, Builder, PropertyProject
from agents.models import Agent
from deals.models import Deal
from deals.models_commission import Commission
from wallet.models import Wallet, WalletTransaction
from saas_core.serializers import (
    LeadSerializer,
    PropertySerializer,
    AgentSerializer,
    DealSerializer,
    WalletSerializer,
    WalletTransactionSerializer,
    CommissionSerializer,
    BuilderSerializer,
    PropertyProjectSerializer,
)
from saas_core.api import IsCompanyMember, RoleRequired, CompanyQuerysetMixin
from django.db import transaction
from decimal import Decimal
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters


class LeadViewSet(CompanyQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = LeadSerializer
    permission_classes = [IsAuthenticated, IsCompanyMember]
    allowed_roles = ["admin", "super_admin", "agent", "sub_agent", "accountant"]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "stage", "temperature", "assigned_agent"]
    search_fields = ["name", "mobile", "email", "preferred_location"]
    ordering_fields = ["created_at", "updated_at", "lead_score", "budget"]

    def get_queryset(self):
        qs = Lead.objects.all()
        user = self.request.user
        if user.is_superuser:
            return qs
        # Company filter if model has company
        if hasattr(Lead, "company"):
            qs = qs.filter(company=getattr(self.request, "company", None))
        # Agents see only their assigned leads
        if getattr(user, "role", "") in {"agent", "sub_agent"}:
            agent_profile = getattr(user, "agent_profile", None)
            if agent_profile:
                qs = qs.filter(assigned_agent=agent_profile)
            else:
                qs = qs.none()
        return qs

    def perform_create(self, serializer):
        data = {}
        if hasattr(Lead, "company"):
            data["company"] = getattr(self.request, "company", None)
        serializer.save(created_by=self.request.user, **data)

    @action(detail=True, methods=["post"])
    def status(self, request, pk=None):
        lead = self.get_object()
        payload = request.data or {}
        fields = {}
        for key in ["status", "stage", "temperature", "budget", "preferred_location", "lead_score"]:
            if key in payload:
                fields[key] = payload[key]
        for key, val in fields.items():
            setattr(lead, key, val)
        lead.save(update_fields=list(fields.keys()))
        return Response(self.get_serializer(lead).data)

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        lead = self.get_object()
        agent_id = request.data.get("agent_id")
        if not agent_id:
            return Response({"detail": "agent_id required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            agent = Agent.objects.get(id=agent_id)
        except Agent.DoesNotExist:
            return Response({"detail": "Agent not found"}, status=status.HTTP_404_NOT_FOUND)
        lead.assigned_agent = agent
        lead.save(update_fields=["assigned_agent"])
        return Response(self.get_serializer(lead).data)


class AgentViewSet(CompanyQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = AgentSerializer
    permission_classes = [IsAuthenticated, IsCompanyMember]
    allowed_roles = ["admin", "super_admin"]

    def get_queryset(self):
        qs = Agent.objects.select_related("user")
        if self.request.user.is_superuser:
            return qs
        if hasattr(Agent, "company"):
            qs = qs.filter(company=getattr(self.request, "company", None))
        return qs


class DealViewSet(CompanyQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = DealSerializer
    permission_classes = [IsAuthenticated, IsCompanyMember]
    allowed_roles = ["admin", "super_admin", "agent", "sub_agent"]

    def get_queryset(self):
        qs = Deal.objects.select_related("agent")
        user = self.request.user
        if user.is_superuser:
            return qs
        if hasattr(Deal, "company"):
            qs = qs.filter(company=getattr(self.request, "company", None))
        if getattr(user, "role", "") in {"agent", "sub_agent"}:
            agent_profile = getattr(user, "agent_profile", None)
            if agent_profile:
                qs = qs.filter(agent=agent_profile)
            else:
                qs = qs.none()
        return qs

    def perform_create(self, serializer):
        data = {}
        if hasattr(Deal, "company"):
            data["company"] = getattr(self.request, "company", None)
        deal = serializer.save(**data)
        self._ensure_commission(deal)

    def _ensure_commission(self, deal: Deal):
        # Simple tier: 100% of commission_amount split admin 30 / agent 60 / sub-agent 10 (if present)
        total = getattr(deal, "commission_amount", Decimal("0.00")) or Decimal("0.00")
        if total <= 0:
            return
        agent = getattr(deal, "agent", None)
        sub_agent_amount = Decimal("0.00")
        agent_amount = total * Decimal("0.60")
        admin_amount = total * Decimal("0.40")
        if agent and getattr(agent, "parent_agent", None):
            sub_agent_amount = total * Decimal("0.10")
            agent_amount = total * Decimal("0.50")
            admin_amount = total - agent_amount - sub_agent_amount
        Commission.objects.update_or_create(
            deal=deal,
            defaults={
                "company": getattr(deal, "company", None),
                "admin_amount": admin_amount,
                "agent_amount": agent_amount,
                "sub_agent_amount": sub_agent_amount,
                "total_amount": total,
            },
        )


class PropertyViewSet(CompanyQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = PropertySerializer
    permission_classes = [IsAuthenticated, IsCompanyMember]
    allowed_roles = ["admin", "super_admin", "agent", "sub_agent"]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["city", "property_type", "builder"]
    search_fields = ["title", "location", "city", "description"]
    ordering_fields = ["created_at", "price"]

    def get_queryset(self):
        qs = Property.objects.all()
        if self.request.user.is_superuser:
            return qs
        if hasattr(Property, "company"):
            qs = qs.filter(company=getattr(self.request, "company", None))
        return qs

    def perform_create(self, serializer):
        data = {}
        if hasattr(Property, "company"):
            data["company"] = getattr(self.request, "company", None)
        builder = serializer.validated_data.get("builder")
        company = data.get("company")
        if builder and company and getattr(builder, "company_id", None) and builder.company_id != getattr(company, "id", None):
            raise ValidationError({"builder": "Builder does not belong to this company"})
        serializer.save(**data)


class BuilderViewSet(CompanyQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = BuilderSerializer
    permission_classes = [IsAuthenticated, IsCompanyMember]
    allowed_roles = ["admin", "super_admin", "agent", "sub_agent"]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "company_name", "contact"]
    ordering_fields = ["created_at", "name"]

    def get_queryset(self):
        qs = Builder.objects.all()
        if self.request.user.is_superuser:
            return qs
        if hasattr(Builder, "company"):
            qs = qs.filter(company=getattr(self.request, "company", None))
        return qs

    def perform_create(self, serializer):
        data = {}
        if hasattr(Builder, "company"):
            data["company"] = getattr(self.request, "company", None)
        serializer.save(**data)


class PropertyProjectViewSet(CompanyQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = PropertyProjectSerializer
    permission_classes = [IsAuthenticated, IsCompanyMember]
    allowed_roles = ["admin", "super_admin", "agent", "sub_agent"]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["builder", "approved"]
    search_fields = ["title", "location", "description"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        qs = PropertyProject.objects.select_related("builder")
        if self.request.user.is_superuser:
            return qs
        if hasattr(PropertyProject, "company"):
            qs = qs.filter(company=getattr(self.request, "company", None))
        return qs

    def perform_create(self, serializer):
        data = {}
        if hasattr(PropertyProject, "company"):
            data["company"] = getattr(self.request, "company", None)
        builder = serializer.validated_data.get("builder")
        company = data.get("company")
        if builder and company and getattr(builder, "company_id", None) and builder.company_id != getattr(company, "id", None):
            raise ValidationError({"builder": "Builder does not belong to this company"})
        serializer.save(**data)


class WalletViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Returns the wallet of the current user.
    """

    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        wallet, _ = Wallet.objects.get_or_create(user=self.request.user)
        return Wallet.objects.filter(pk=wallet.pk)


class WalletTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WalletTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        wallet, _ = Wallet.objects.get_or_create(user=self.request.user)
        return wallet.transactions.all()


class CommissionViewSet(CompanyQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = CommissionSerializer
    permission_classes = [IsAuthenticated, IsCompanyMember]

    def get_queryset(self):
        qs = Commission.objects.select_related("deal")
        if self.request.user.is_superuser:
            return qs
        if hasattr(Commission, "company"):
            qs = qs.filter(company=getattr(self.request, "company", None))
        return qs
