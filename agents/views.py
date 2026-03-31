from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.db.models import Count, Sum
from billing.permissions import FeatureActionPermission
from .kyc import approve_agent_kyc, reject_agent_kyc

from accounts.models import SaaSRole
from deals.models import Deal, Payment
from leads.models import Lead
from .models import Agent, AgentCoverageArea, AgentVerification
from .serializers import AgentCoverageAreaSerializer, AgentSerializer, AgentVerificationSerializer
from .hierarchy import ensure_wallet
from .models import AgentLocationLog, AgentActivityLog
from django.utils import timezone


class AgentViewSet(viewsets.ModelViewSet):
    queryset = Agent.objects.select_related("user", "company").prefetch_related("service_areas")
    serializer_class = AgentSerializer
    permission_classes = [permissions.IsAuthenticated, FeatureActionPermission]
    feature_key = "crm.agents"
    feature_key_map = {
        "dashboard": "crm.agents",
        "set_pincodes": "crm.agents",
        "verify_kyc": "crm.kyc",
        "approve": "crm.kyc",
        "reject": "crm.kyc",
        "wallet_adjust": "crm.wallet",
        "set_parent": "crm.agent_transfers",
        "update_location": "crm.agents",
    }

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        # Allow admins to see all; agents only see their own profile.
        if user.is_superuser or getattr(user, "role", "") in {
            SaaSRole.SUPER_ADMIN,
            SaaSRole.STATE_ADMIN,
            SaaSRole.DISTRICT_ADMIN,
            SaaSRole.AREA_ADMIN,
            SaaSRole.SUPER_AGENT,
        }:
            return qs
        return qs.filter(user=user)

    def perform_create(self, serializer):
        user = self.request.user
        user_for_agent = serializer.validated_data.get("user") or user
        approval_status = (
            Agent.ApprovalStatus.APPROVED
            if (user.is_superuser or getattr(user, "is_staff", False))
            else Agent.ApprovalStatus.PENDING
        )
        serializer.save(user=user_for_agent, approval_status=approval_status)

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def dashboard(self, request):
        qs = self.get_queryset()
        agent = qs.filter(user=request.user).first() if not (request.user.is_superuser or getattr(request.user, "is_staff", False)) else qs.first()
        if not agent:
            return Response({"detail": "agent profile not found"}, status=404)
        assigned_leads = Lead.objects.filter(assigned_agent=agent)
        deals = Deal.objects.filter(agent=agent)
        payouts = Payment.objects.filter(agent=agent, payment_type=Payment.PaymentType.AGENT_PAYOUT)
        return Response(
            {
                "agent": AgentSerializer(agent, context={"request": request}).data,
                "assigned_leads": assigned_leads.count(),
                "open_leads": assigned_leads.exclude(status__in=[Lead.Status.CLOSED, Lead.Status.CONVERTED, Lead.Status.LOST]).count(),
                "converted_leads": assigned_leads.filter(status=Lead.Status.CONVERTED).count(),
                "closed_deals": deals.count(),
                "deal_value": deals.aggregate(total=Sum("deal_amount"))["total"] or 0,
                "pending_payouts": payouts.exclude(status=Payment.Status.PAID).aggregate(total=Sum("amount"))["total"] or 0,
                "coverage_breakdown": list(agent.coverage_areas.values("state", "district").annotate(count=Count("id"))),
            }
        )

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def set_pincodes(self, request, pk=None):
        agent = self.get_object()
        pincodes = request.data.get("pincodes") or []
        if not isinstance(pincodes, list):
            return Response({"detail": "pincodes must be a list"}, status=400)
        agent.pincodes = [str(p).strip() for p in pincodes if str(p).strip()]
        agent.save(update_fields=["pincodes", "updated_at"])
        return Response(self.get_serializer(agent).data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def verify_kyc(self, request, pk=None):
        agent = self.get_object()
        approve_agent_kyc(agent, admin=request.user, remarks=request.data.get("remarks") or "")
        return Response({"detail": "KYC verified"})

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def approve(self, request, pk=None):
        if not (request.user.is_superuser or getattr(request.user, "is_staff", False)):
            raise PermissionDenied("Only admins can approve agents.")
        agent = self.get_object()
        agent.approval_status = Agent.ApprovalStatus.APPROVED
        agent.save(update_fields=["approval_status", "updated_at"])
        approve_agent_kyc(agent, admin=request.user, remarks=request.data.get("remarks") or "")
        return Response({"detail": "Agent approved"})

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def reject(self, request, pk=None):
        if not (request.user.is_superuser or getattr(request.user, "is_staff", False)):
            raise PermissionDenied("Only admins can reject agents.")
        agent = self.get_object()
        agent.approval_status = Agent.ApprovalStatus.REJECTED
        agent.save(update_fields=["approval_status", "updated_at"])
        reject_agent_kyc(agent, admin=request.user, remarks=request.data.get("remarks") or "")
        return Response({"detail": "Agent rejected"})

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def wallet_adjust(self, request, pk=None):
        agent = self.get_object()
        amount = request.data.get("amount")
        try:
            amount = float(amount)
        except Exception:
            return Response({"detail": "amount must be numeric"}, status=400)
        tx_type = request.data.get("type", "credit")
        source = request.data.get("source", "adjustment")
        note = request.data.get("note", "")
        wallet = ensure_wallet(agent)
        if tx_type == "debit":
            wallet.debit(amount, source=source, note=note)
        else:
            wallet.credit(amount, source=source, note=note)
        return Response({"balance": wallet.balance})

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def set_parent(self, request, pk=None):
        agent = self.get_object()
        parent_id = request.data.get("parent_agent")
        if not parent_id:
            agent.parent_agent = None
        else:
            parent = Agent.objects.filter(id=parent_id).first()
            if not parent:
                return Response({"detail": "Parent agent not found"}, status=404)
            agent.parent_agent = parent
        agent.save(update_fields=["parent_agent", "updated_at"])
        return Response(self.get_serializer(agent).data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def update_location(self, request, pk=None):
        agent = self.get_object()
        lat = request.data.get("latitude")
        lng = request.data.get("longitude")
        accuracy = request.data.get("accuracy")
        try:
            lat = float(lat)
            lng = float(lng)
        except Exception:
            return Response({"detail": "latitude/longitude required"}, status=400)

        AgentLocationLog.objects.create(agent=agent, latitude=lat, longitude=lng, accuracy=accuracy or None)
        now = timezone.now()
        agent.last_latitude = lat
        agent.last_longitude = lng
        agent.current_latitude = lat
        agent.current_longitude = lng
        agent.last_ping_at = now
        agent.location_updated_at = now
        agent.save(
            update_fields=[
                "last_latitude",
                "last_longitude",
                "current_latitude",
                "current_longitude",
                "last_ping_at",
                "location_updated_at",
                "updated_at",
            ]
        )
        AgentActivityLog.objects.create(agent=agent, action="location_update", metadata={"lat": lat, "lng": lng})
        return Response({"detail": "location updated"})


class AgentCoverageAreaViewSet(viewsets.ModelViewSet):
    queryset = AgentCoverageArea.objects.select_related("agent", "agent__user")
    serializer_class = AgentCoverageAreaSerializer
    permission_classes = [permissions.IsAuthenticated, FeatureActionPermission]
    feature_key = "crm.agents"

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or getattr(user, "is_staff", False):
            return qs
        return qs.filter(agent__user=user)

    def perform_create(self, serializer):
        user = self.request.user
        if user.is_superuser or getattr(user, "is_staff", False):
            serializer.save()
            return
        agent = Agent.objects.filter(user=user).first()
        if not agent:
            raise PermissionDenied("Create an agent profile before adding coverage areas.")
        serializer.save(agent=agent)


class AgentVerificationViewSet(viewsets.ModelViewSet):
    queryset = AgentVerification.objects.select_related("agent", "agent__user", "verified_by")
    serializer_class = AgentVerificationSerializer
    permission_classes = [permissions.IsAuthenticated, FeatureActionPermission]
    feature_key = "crm.kyc"

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or getattr(user, "is_staff", False):
            return qs
        return qs.filter(agent__user=user)

    def perform_create(self, serializer):
        user = self.request.user
        if user.is_superuser or getattr(user, "is_staff", False):
            serializer.save()
            return
        agent = Agent.objects.filter(user=user).first()
        if not agent:
            raise PermissionDenied("Create an agent profile before uploading verification documents.")
        serializer.save(agent=agent)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def approve(self, request, pk=None):
        if not (request.user.is_superuser or getattr(request.user, "is_staff", False)):
            raise PermissionDenied("Only admins can approve verification records.")
        verification = self.get_object()
        verification.status = AgentVerification.Status.APPROVED
        verification.verified_by = request.user
        verification.reviewed_at = timezone.now()
        verification.save(update_fields=["status", "verified_by", "reviewed_at", "updated_at"])
        if verification.document_type == AgentVerification.DocumentType.LICENSE and not verification.agent.license_number:
            verification.agent.license_number = f"VERIFIED-{verification.agent_id}"
            verification.agent.kyc_verified = True
            verification.agent.save(update_fields=["license_number", "kyc_verified", "updated_at"])
        return Response(self.get_serializer(verification).data)

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def reject(self, request, pk=None):
        if not (request.user.is_superuser or getattr(request.user, "is_staff", False)):
            raise PermissionDenied("Only admins can reject verification records.")
        verification = self.get_object()
        verification.status = AgentVerification.Status.REJECTED
        verification.verified_by = request.user
        verification.reviewed_at = timezone.now()
        verification.remarks = str(request.data.get("remarks") or verification.remarks or "")[:255]
        verification.save(update_fields=["status", "verified_by", "reviewed_at", "remarks", "updated_at"])
        return Response(self.get_serializer(verification).data)
