from decimal import Decimal
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from billing.permissions import FeatureActionPermission

from agents.models import Agent
try:
    from payments.models import PaymentTransaction
except Exception:
    PaymentTransaction = None
from visits.models import SiteVisit
from visits.serializers import SiteVisitSerializer
from leads.pipeline import move_stage
from payouts.services import create_payout_for_lead
from payouts.wallet_system import credit_on_lead_close
from rewards.services import evaluate_rewards_for_agent
from .models import (
    Agreement,
    Builder,
    FollowUp,
    Lead,
    LeadActivity,
    LeadAssignment,
    LeadAssignmentLog,
    LeadImportBatch,
    LeadDocument,
    LeadSource,
    Property,
    PropertyFeature,
    PropertyImage,
    PropertyLocation,
    PropertyMedia,
    PropertyVideo,
    PropertyProject,
    PropertyView,
    PropertyWishlist,
)
from .serializers import (
    LeadActivitySerializer,
    LeadAssignmentSerializer,
    LeadAssignmentLogSerializer,
    LeadBulkAssignSerializer,
    LeadCaptureSerializer,
    LeadContactSerializer,
    LeadConvertSerializer,
    LeadCSVImportSerializer,
    LeadImportBatchSerializer,
    LeadSerializer,
    LeadSourceSerializer,
    LeadScrapeSerializer,
    BuilderSerializer,
    PropertyMediaSerializer,
    PropertyFeatureSerializer,
    PropertyImageSerializer,
    PropertyLocationSerializer,
    PropertySerializer,
    PropertyVideoSerializer,
    PropertyProjectSerializer,
    PropertyViewSerializer,
    PropertyWishlistSerializer,
    FollowUpLeadSerializer,
    LeadDocumentSerializer,
    AgreementSerializer,
)
from .services import (
    assign_lead,
    assign_lead_by_geo,
    auto_assign_lead,
    build_lead_timeline,
    build_monitoring_snapshot,
    bulk_assign_leads,
    convert_lead,
    extract_lead_data_from_photo,
    import_leads_from_rows,
    ingest_lead_payload,
    match_properties_for_lead,
    process_due_followups,
    parse_lead_import_file,
    merge_duplicate_leads,
    reassign_stale_leads,
    resolve_source_config,
    schedule_followup,
    scrape_leads_from_page,
    send_inactive_lead_followups,
    send_lead_message,
    lock_lead,
    unlock_lead,
    user_can_edit_lead,
)


def _is_admin_user(user):
    role = (getattr(user, "role", "") or "").strip().lower()
    return user.is_superuser or getattr(user, "is_staff", False) or role in {"admin", "super_admin", "state_admin", "district_admin", "area_admin"}


class LeadViewSet(viewsets.ModelViewSet):
    queryset = Lead.objects.select_related(
        "assigned_agent",
        "assigned_to",
        "pincode",
        "interested_property",
        "source_config",
        "converted_customer",
    ).prefetch_related("assignments")
    serializer_class = LeadSerializer
    permission_classes = [permissions.IsAuthenticated, FeatureActionPermission]
    feature_key = "crm.leads"

    def _company(self):
        return getattr(self.request.user, "company", None)

    def _is_admin(self, user):
        return _is_admin_user(user)

    def _assert_editable(self, lead):
        if not user_can_edit_lead(self.request.user, lead):
            raise PermissionDenied("This lead is locked to another agent.")

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_superuser:
            company = self._company()
            qs = qs.filter(models.Q(company=company) | models.Q(company__isnull=True))
            role = (getattr(user, "role", "") or "").strip().lower()
            if role in {"agent", "super_agent", "area_admin"}:
                qs = qs.filter(models.Q(assigned_to=user) | models.Q(assigned_agent__user=user))
            elif role == "customer":
                qs = qs.filter(models.Q(created_by=user) | models.Q(converted_customer__user=user))
        if status_filter := self.request.query_params.get("status"):
            qs = qs.filter(status=status_filter)
        if stage := self.request.query_params.get("stage"):
            qs = qs.filter(stage=stage)
        if source := self.request.query_params.get("source"):
            qs = qs.filter(source=source)
        if agent_id := self.request.query_params.get("agent"):
            qs = qs.filter(assigned_agent_id=agent_id)
        if search := (self.request.query_params.get("search") or "").strip():
            qs = qs.filter(
                models.Q(name__icontains=search)
                | models.Q(mobile__icontains=search)
                | models.Q(email__icontains=search)
                | models.Q(city__icontains=search)
                | models.Q(district__icontains=search)
                | models.Q(state__icontains=search)
            )
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        company = self._company()
        data = serializer.validated_data
        lead, _ = ingest_lead_payload(
            {
                "name": data.get("name"),
                "phone": data.get("mobile"),
                "email": data.get("email"),
                "source": data.get("source"),
                "status": data.get("status"),
                "stage": data.get("stage"),
                "interest_type": data.get("interest_type"),
                "deal_value": data.get("deal_value"),
                "property_type": data.get("property_type"),
                "budget": data.get("budget"),
                "preferred_location": data.get("preferred_location"),
                "geo_location": data.get("geo_location"),
                "country": data.get("country"),
                "state": data.get("state"),
                "district": data.get("district"),
                "tehsil": data.get("tehsil"),
                "village": data.get("village"),
                "city": data.get("city"),
                "pincode_text": data.get("pincode_text"),
                "notes": data.get("notes"),
                "metadata": data.get("metadata"),
            },
            company=company,
            actor=user,
            source_config=data.get("source_config"),
            auto_assign=True,
        )
        serializer.instance = lead

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        if not self._is_admin(request.user):
            raise PermissionDenied("Only admins can assign leads.")
        lead = self.get_object()
        agent_id = request.data.get("agent")
        if not agent_id:
            return Response({"detail": "agent is required"}, status=400)
        agent = Agent.objects.filter(id=agent_id).first()
        if not agent:
            return Response({"detail": "agent not found"}, status=404)
        assign_lead(
            lead,
            agent=agent,
            actor=request.user,
            reason=str(request.data.get("reason") or "Manual reassignment"),
            match_level="manual",
            assignment_type=LeadAssignmentLog.AssignmentType.REASSIGN if lead.assigned_agent_id else LeadAssignmentLog.AssignmentType.MANUAL,
        )
        return Response(LeadSerializer(lead, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def merge(self, request, pk=None):
        if not self._is_admin(request.user):
            raise PermissionDenied("Only admins can merge leads.")
        lead = self.get_object()
        duplicate_id = request.data.get("duplicate_id") or request.data.get("duplicate")
        if not duplicate_id:
            return Response({"detail": "duplicate_id is required"}, status=400)
        duplicate = self.get_queryset().filter(id=duplicate_id).first()
        if not duplicate:
            return Response({"detail": "duplicate lead not found"}, status=404)
        merged = merge_duplicate_leads(
            primary=lead,
            duplicate=duplicate,
            actor=request.user,
            note=str(request.data.get("note") or "Dashboard merge"),
        )
        return Response(LeadSerializer(merged, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def status(self, request, pk=None):
        lead = self.get_object()
        self._assert_editable(lead)
        new_status = request.data.get("status")
        if new_status not in dict(Lead.Status.choices):
            return Response({"detail": "Invalid status"}, status=400)

        payment_amount = request.data.get("payment_amount")
        if payment_amount is not None and PaymentTransaction:
            try:
                amount = Decimal(str(payment_amount))
            except Exception:
                return Response({"detail": "payment_amount must be numeric"}, status=400)
            mode = request.data.get("payment_mode") or PaymentTransaction.Mode.RAZORPAY
            if mode not in PaymentTransaction.Mode.values:
                mode = PaymentTransaction.Mode.CASH
            PaymentTransaction.objects.create(
                user=lead.assigned_to,
                amount=amount,
                mode=mode,
                status=PaymentTransaction.Status.SUCCESS,
                payload={"lead_id": lead.id, "note": "Lead closure payment"},
            )
            lead.deal_value = amount
            lead.save(update_fields=["deal_value", "updated_at"])

        create_payment = str(request.data.get("create_payment", "true")).strip().lower() not in {"0", "false", "no", "off"}
        if new_status == Lead.Status.CONVERTED:
            conversion = convert_lead(
                lead,
                actor=request.user,
                deal_amount=request.data.get("deal_amount") or request.data.get("payment_amount") or lead.deal_value,
                commission_rate=request.data.get("commission_rate"),
                company_share_percent=request.data.get("company_share_percent"),
                agent_share_percent=request.data.get("agent_share_percent"),
                customer_name=request.data.get("customer_name") or lead.name,
                customer_email=request.data.get("customer_email") or lead.email,
                customer_phone=request.data.get("customer_phone") or lead.mobile,
                create_payment=create_payment,
                note=str(request.data.get("note") or ""),
            )
            return Response(
                {
                    "lead": LeadSerializer(conversion["lead"], context={"request": request}).data,
                    "deal_id": conversion["deal"].id,
                    "customer_id": conversion["customer"].id,
                }
            )

        lead.mark_status(new_status, actor=request.user, note=str(request.data.get("note") or ""))
        # Optional stage update if provided
        stage = request.data.get("stage")
        if stage in dict(Lead.Stage.choices):
            move_stage(lead, stage, actor=request.user, note="Stage updated via status action")

        # If closed, create payout and rewards
        if new_status == Lead.Status.CLOSED and lead.assigned_agent_id:
            create_payout_for_lead(lead, generated_by=request.user)
            evaluate_rewards_for_agent(lead.assigned_agent)
            credit_on_lead_close(lead)

        return Response(LeadSerializer(lead, context={"request": request}).data)

    @action(detail=True, methods=["get"])
    def recommended_properties(self, request, pk=None):
        lead = self.get_object()
        props = match_properties_for_lead(lead)
        return Response(PropertySerializer(props, many=True, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def add_note(self, request, pk=None):
        lead = self.get_object()
        self._assert_editable(lead)
        note = str(request.data.get("note") or "").strip()
        if not note:
            return Response({"detail": "note is required"}, status=400)
        LeadActivity.objects.create(
            lead=lead,
            actor=request.user,
            activity_type="note",
            note=note[:500],
        )
        return Response({"detail": "noted"})

    @action(detail=True, methods=["post"])
    def contact(self, request, pk=None):
        lead = self.get_object()
        self._assert_editable(lead)
        serializer = LeadContactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = send_lead_message(
            lead,
            actor=request.user,
            channel=serializer.validated_data["channel"],
            message=serializer.validated_data.get("message", ""),
            subject=serializer.validated_data.get("subject", ""),
            phone=serializer.validated_data.get("phone", ""),
            email=serializer.validated_data.get("email", ""),
            metadata=serializer.validated_data.get("metadata") or {},
        )
        return Response({"detail": "logged", "payload": payload})

    @action(detail=True, methods=["get"])
    def timeline(self, request, pk=None):
        lead = self.get_object()
        return Response(build_lead_timeline(lead))

    @action(detail=True, methods=["post"])
    def convert(self, request, pk=None):
        lead = self.get_object()
        self._assert_editable(lead)
        serializer = LeadConvertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conversion = convert_lead(lead, actor=request.user, **serializer.validated_data)
        return Response(
            {
                "lead": LeadSerializer(conversion["lead"], context={"request": request}).data,
                "deal_id": conversion["deal"].id,
                "customer_id": conversion["customer"].id,
            }
        )

    @action(detail=False, methods=["post"])
    def bulk_assign(self, request):
        if not self._is_admin(request.user):
            raise PermissionDenied("Only admins can bulk assign leads.")
        serializer = LeadBulkAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lead_ids = serializer.validated_data["lead_ids"]
        qs = self.get_queryset().filter(id__in=lead_ids)
        agent = None
        if serializer.validated_data.get("agent"):
            agent = Agent.objects.filter(id=serializer.validated_data["agent"]).first()
            if not agent:
                return Response({"detail": "agent not found"}, status=404)
        updated = bulk_assign_leads(
            leads=list(qs),
            agent=agent,
            actor=request.user,
            reason=serializer.validated_data.get("reason", ""),
            auto=serializer.validated_data.get("auto", False),
        )
        return Response(LeadSerializer(updated, many=True, context={"request": request}).data)

    @action(detail=False, methods=["get"])
    def dashboard_summary(self, request):
        qs = self.get_queryset()
        city = request.query_params.get("city")
        agent_id = request.query_params.get("agent")
        source = request.query_params.get("source")

        if city:
            qs = qs.filter(assigned_agent__city__iexact=city)
        if agent_id:
            qs = qs.filter(assigned_agent_id=agent_id)
        if source:
            qs = qs.filter(source=source)

        monitoring = build_monitoring_snapshot(qs)
        closed_qs = qs.filter(status__in=[Lead.Status.CONVERTED, Lead.Status.CLOSED])
        visits_qs = SiteVisit.objects.all()
        if agent_id:
            visits_qs = visits_qs.filter(agent_id=agent_id)
        if city:
            visits_qs = visits_qs.filter(agent__city__iexact=city)

        data = {
            **monitoring,
            "site_visits": visits_qs.count(),
            "total_revenue": closed_qs.aggregate(total=models.Sum("deal_value"))["total"] or 0,
            "agent_performance": list(
                closed_qs.values("assigned_agent", "assigned_agent__name").annotate(
                    closed=models.Count("id"),
                    revenue=models.Sum("deal_value"),
                )
            ),
            "active_agents": Agent.objects.filter(is_active=True).count(),
            "inactive_agents": Agent.objects.filter(is_active=False).count(),
            "top_property_locations": list(
                Property.objects.exclude(status=Property.Status.REJECTED)
                .values("city", "district", "state")
                .annotate(count=models.Count("id"))
                .order_by("-count")[:5]
            ),
        }
        return Response(data)

    @action(detail=False, methods=["get"])
    def monitoring(self, request):
        qs = self.get_queryset()
        return Response(build_monitoring_snapshot(qs))

    @action(detail=False, methods=["get"])
    def kanban(self, request):
        qs = self.get_queryset()
        columns = []
        for stage_value, stage_label in Lead.Stage.choices:
            stage_qs = qs.filter(stage=stage_value)[:50]
            columns.append(
                {
                    "stage": stage_value,
                    "label": stage_label,
                    "count": qs.filter(stage=stage_value).count(),
                    "leads": LeadSerializer(stage_qs, many=True, context={"request": request}).data,
                }
            )
        return Response(columns)

    @action(detail=False, methods=["post"])
    def import_csv(self, request):
        if not self._is_admin(request.user):
            raise PermissionDenied("Only admins can import leads.")
        serializer = LeadCSVImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        upload = serializer.validated_data["file"]
        source_name = serializer.validated_data.get("source") or "Upload"
        source_config = resolve_source_config(
            company=self._company(),
            source_key=serializer.validated_data.get("source_key", ""),
            source_value=Lead.Source.MANUAL,
        )
        preview = parse_lead_import_file(
            upload,
            mapping=serializer.validated_data.get("mapping"),
            preview_limit=25,
        )
        if serializer.validated_data.get("preview_only"):
            return Response(
                {
                    "detail": "preview ready",
                    "file_type": preview["file_type"],
                    "headers": preview["headers"],
                    "preview_rows": preview["preview_rows"],
                    "issues": preview["issues"],
                    "total_rows": preview["total_rows"],
                },
                status=status.HTTP_200_OK,
            )
        batch = import_leads_from_rows(
            preview["rows"],
            company=self._company(),
            actor=request.user,
            source_config=source_config,
            import_type=LeadImportBatch.ImportType.CSV,
            source_name=source_name,
            auto_assign=serializer.validated_data.get("auto_assign", True),
        )
        return Response(LeadImportBatchSerializer(batch, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def import_preview(self, request):
        if not self._is_admin(request.user):
            raise PermissionDenied("Only admins can preview lead imports.")
        serializer = LeadCSVImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        preview = parse_lead_import_file(
            serializer.validated_data["file"],
            mapping=serializer.validated_data.get("mapping"),
            preview_limit=25,
        )
        return Response(
            {
                "detail": "preview ready",
                "file_type": preview["file_type"],
                "headers": preview["headers"],
                "preview_rows": preview["preview_rows"],
                "issues": preview["issues"],
                "total_rows": preview["total_rows"],
            }
        )

    @action(detail=False, methods=["post"])
    def scrape(self, request):
        if not self._is_admin(request.user):
            raise PermissionDenied("Only admins can scrape leads.")
        serializer = LeadScrapeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        raw_html = data.get("raw_html") or ""
        url = data.get("url") or "about:blank"
        if not raw_html and not data.get("url"):
            return Response({"detail": "url or raw_html is required"}, status=400)
        company = self._company()
        source_config = resolve_source_config(
            company=company,
            source_key=data.get("source_key", ""),
            source_value=data.get("source", Lead.Source.WEBSITE),
        )
        batch, rows = scrape_leads_from_page(
            url=url,
            company=company,
            actor=request.user,
            source_config=source_config,
            auto_assign=data.get("auto_assign", True),
            max_items=data.get("max_items", 25),
            raw_html=raw_html,
        )
        return Response(
            {
                "detail": "scrape completed",
                "batch": LeadImportBatchSerializer(batch, context={"request": request}).data,
                "rows_extracted": len(rows),
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def log_call(self, request, pk=None):
        lead = self.get_object()
        from crm.models import CallLog
        from crm.serializers import CallLogSerializer

        serializer = CallLogSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        call = serializer.save(agent=request.user, lead=lead)
        return Response(CallLogSerializer(call, context={"request": request}).data, status=status.HTTP_201_CREATED)


class LeadActivityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LeadActivity.objects.select_related("lead", "actor").all()
    serializer_class = LeadActivitySerializer
    permission_classes = [permissions.IsAuthenticated, FeatureActionPermission]
    feature_key = "crm.reports"

    def _company(self):
        return getattr(self.request.user, "company", None)

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs
        if getattr(user, "role", "") == "customer":
            return qs.filter(models.Q(lead__created_by=user) | models.Q(lead__converted_customer__user=user))
        company = self._company()
        return qs.filter(models.Q(lead__company=company) | models.Q(lead__company__isnull=True))


class LeadAssignmentLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LeadAssignmentLog.objects.select_related("lead", "agent", "assigned_by")
    serializer_class = LeadAssignmentLogSerializer
    permission_classes = [permissions.IsAuthenticated, FeatureActionPermission]
    feature_key = "crm.reports"

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs
        if getattr(user, "role", "") == "customer":
            return qs.filter(models.Q(lead__created_by=user) | models.Q(lead__converted_customer__user=user))
        company = getattr(user, "company", None)
        return qs.filter(models.Q(lead__company=company) | models.Q(lead__assigned_to=user) | models.Q(lead__assigned_agent__user=user))


class LeadAssignmentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LeadAssignment.objects.select_related("lead", "agent", "assigned_by", "agent__user")
    serializer_class = LeadAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated, FeatureActionPermission]
    feature_key = "crm.leads"

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs
        company = getattr(user, "company", None)
        role = (getattr(user, "role", "") or "").strip().lower()
        if role == "customer":
            return qs.filter(lead__converted_customer__user=user)
        if role in {"agent", "super_agent", "area_admin"}:
            return qs.filter(agent__user=user)
        return qs.filter(models.Q(lead__company=company) | models.Q(lead__company__isnull=True))


class LeadSourceViewSet(viewsets.ModelViewSet):
    queryset = LeadSource.objects.all()
    serializer_class = LeadSourceSerializer
    permission_classes = [permissions.IsAuthenticated, FeatureActionPermission]
    feature_key = "crm.leads"

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs
        company = getattr(user, "company", None)
        return qs.filter(models.Q(company=company) | models.Q(company__isnull=True))

    def perform_create(self, serializer):
        serializer.save(company=getattr(self.request.user, "company", None))


class LeadImportBatchViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LeadImportBatch.objects.select_related("source", "created_by")
    serializer_class = LeadImportBatchSerializer
    permission_classes = [permissions.IsAuthenticated, FeatureActionPermission]
    feature_key = "crm.leads"

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs
        company = getattr(user, "company", None)
        return qs.filter(models.Q(company=company) | models.Q(company__isnull=True))


class PropertyViewSet(viewsets.ModelViewSet):
    queryset = Property.objects.select_related("builder", "assigned_agent", "owner").prefetch_related(
        "media",
        "wishlist_entries",
        "images",
        "videos",
        "features",
        "location_detail",
    )
    serializer_class = PropertySerializer
    permission_classes = [permissions.IsAuthenticated, FeatureActionPermission]
    feature_key = "crm.properties"

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs
        company = getattr(user, "company", None)
        if company:
            qs = qs.filter(models.Q(company=company) | models.Q(company__isnull=True))
        else:
            qs = qs.filter(company__isnull=True)
        if getattr(user, "role", "") == "customer":
            qs = qs.exclude(status=Property.Status.REJECTED)
            customer = getattr(user, "customer_profile", None)
            if customer:
                location_filters = models.Q()
                if customer.pin_code:
                    location_filters |= models.Q(pin_code=customer.pin_code)
                if customer.city:
                    location_filters |= models.Q(city__iexact=customer.city)
                if customer.district:
                    location_filters |= models.Q(district__iexact=customer.district)
                if customer.state:
                    location_filters |= models.Q(state__iexact=customer.state)
                if location_filters:
                    qs = qs.filter(location_filters)
        if city := self.request.query_params.get("city"):
            qs = qs.filter(city__iexact=city)
        if district := self.request.query_params.get("district"):
            qs = qs.filter(district__iexact=district)
        if state := self.request.query_params.get("state"):
            qs = qs.filter(state__iexact=state)
        if pin_code := self.request.query_params.get("pin_code"):
            qs = qs.filter(pin_code=pin_code)
        if property_type := self.request.query_params.get("property_type"):
            qs = qs.filter(property_type=property_type)
        if listing_type := self.request.query_params.get("listing_type"):
            qs = qs.filter(listing_type=listing_type)
        if data_source := self.request.query_params.get("data_source"):
            qs = qs.filter(data_source=data_source)
        if aggregated := self.request.query_params.get("aggregated_property"):
            qs = qs.filter(aggregated_property=str(aggregated).lower() in {"1", "true", "yes", "on"})
        if bedrooms := self.request.query_params.get("bedrooms"):
            qs = qs.filter(bedrooms=bedrooms)
        if bathrooms := self.request.query_params.get("bathrooms"):
            qs = qs.filter(bathrooms=bathrooms)
        if min_price := self.request.query_params.get("min_price"):
            qs = qs.filter(price__gte=min_price)
        if max_price := self.request.query_params.get("max_price"):
            qs = qs.filter(price__lte=max_price)
        if min_area := self.request.query_params.get("min_area_sqft"):
            qs = qs.filter(area_sqft__gte=min_area)
        if max_area := self.request.query_params.get("max_area_sqft"):
            qs = qs.filter(area_sqft__lte=max_area)
        if status_filter := self.request.query_params.get("status"):
            qs = qs.filter(status=status_filter)
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        property_obj = serializer.save(owner=serializer.validated_data.get("owner") or user, company=getattr(user, "company", None))
        PropertyLocation.objects.update_or_create(
            property=property_obj,
            defaults={
                "address": property_obj.location,
                "city": property_obj.city,
                "district": property_obj.district,
                "state": property_obj.state,
                "pin_code": property_obj.pin_code,
                "latitude": property_obj.latitude,
                "longitude": property_obj.longitude,
            },
        )

    def perform_update(self, serializer):
        property_obj = serializer.save()
        PropertyLocation.objects.update_or_create(
            property=property_obj,
            defaults={
                "address": property_obj.location,
                "city": property_obj.city,
                "district": property_obj.district,
                "state": property_obj.state,
                "pin_code": property_obj.pin_code,
                "latitude": property_obj.latitude,
                "longitude": property_obj.longitude,
            },
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        if not (request.user.is_superuser or getattr(request.user, "is_staff", False)):
            raise PermissionDenied("Only admins can approve listings.")
        obj = self.get_object()
        obj.status = Property.Status.APPROVED
        obj.approved_at = timezone.now()
        obj.save(update_fields=["status", "approved_at", "updated_at"])
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        if not (request.user.is_superuser or getattr(request.user, "is_staff", False)):
            raise PermissionDenied("Only admins can reject listings.")
        obj = self.get_object()
        obj.status = Property.Status.REJECTED
        obj.save(update_fields=["status"])
        return Response(self.get_serializer(obj).data)

    @action(detail=True, methods=["post"])
    def wishlist(self, request, pk=None):
        obj = self.get_object()
        wishlist, created = PropertyWishlist.objects.get_or_create(property=obj, user=request.user)
        if not created:
            wishlist.delete()
            return Response({"wishlisted": False, "wishlist_count": obj.wishlist_entries.count()})
        return Response({"wishlisted": True, "wishlist_count": obj.wishlist_entries.count()})

    @action(detail=False, methods=["get"])
    def my_wishlist(self, request):
        wishlist = PropertyWishlist.objects.filter(user=request.user).select_related("property", "property__assigned_agent", "property__owner")
        return Response(PropertyWishlistSerializer(wishlist, many=True, context={"request": request}).data)

    @action(detail=False, methods=["get"])
    def compare(self, request):
        ids = [x.strip() for x in (request.query_params.get("ids") or "").split(",") if x.strip()]
        qs = self.get_queryset().filter(id__in=ids)
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=True, methods=["post"])
    def schedule_visit(self, request, pk=None):
        obj = self.get_object()
        visit_date = parse_datetime(str(request.data.get("visit_date") or "")) or (timezone.now() + timedelta(days=1))
        lead_defaults = {
            "company": getattr(request.user, "company", None),
            "name": request.user.get_full_name() or request.user.username or request.user.email or request.user.mobile or "Property Inquiry",
            "email": request.user.email or "",
            "mobile": request.user.mobile or "",
            "preferred_location": obj.city,
            "city": obj.city,
            "district": obj.district,
            "state": obj.state,
            "country": obj.country,
            "pincode_text": obj.pin_code,
            "property_type": obj.property_type,
            "preferred_property_type": obj.property_type,
            "budget": obj.price,
            "stage": Lead.Stage.VISIT_SCHEDULED,
            "source": Lead.Source.WEBSITE,
            "notes": str(request.data.get("notes") or ""),
        }
        lead, created = Lead.objects.get_or_create(
            interested_property=obj,
            created_by=request.user,
            defaults=lead_defaults,
        )
        if not created:
            for field, value in lead_defaults.items():
                if value and not getattr(lead, field):
                    setattr(lead, field, value)
            lead.stage = Lead.Stage.VISIT_SCHEDULED
            lead.save()
        if not lead.assigned_agent_id:
            auto_assign_lead(lead=lead, fallback_agent=obj.assigned_agent)
        if not lead.assigned_agent_id:
            return Response({"detail": "No active agent available for this visit yet."}, status=400)
        visit = SiteVisit.objects.create(
            lead=lead,
            agent=lead.assigned_agent,
            visit_date=visit_date,
            location=obj.location or obj.city,
            notes=str(request.data.get("notes") or ""),
        )
        try:
            from communication.services import queue_notification_event

            queue_notification_event(
                users=[lead.assigned_agent.user],
                title="Visit scheduled",
                body=f"Visit scheduled for {obj.title} on {visit.visit_date}.",
                lead=lead,
                channels=["in_app", "email", "sms", "whatsapp"],
                email=getattr(lead.assigned_agent.user, "email", ""),
                phone=getattr(lead.assigned_agent.user, "mobile", ""),
                whatsapp_number=getattr(lead.assigned_agent, "phone", ""),
                sender=request.user,
                metadata={"visit_id": visit.id, "property_id": obj.id},
            )
        except Exception:
            pass
        return Response(SiteVisitSerializer(visit, context={"request": request}).data, status=status.HTTP_201_CREATED)


class BuilderViewSet(viewsets.ModelViewSet):
    queryset = Builder.objects.all()
    serializer_class = BuilderSerializer
    permission_classes = [permissions.IsAuthenticated, FeatureActionPermission]
    feature_key = "crm.properties"

    def perform_create(self, serializer):
        serializer.save(company=getattr(self.request.user, "company", None))


class PropertyProjectViewSet(viewsets.ModelViewSet):
    queryset = PropertyProject.objects.select_related("builder").all()
    serializer_class = PropertyProjectSerializer
    permission_classes = [permissions.IsAuthenticated, FeatureActionPermission]
    feature_key = "crm.project_launch"

    def get_queryset(self):
        qs = super().get_queryset()
        if city := self.request.query_params.get("city"):
            qs = qs.filter(city__iexact=city)
        if pre_launch := self.request.query_params.get("pre_launch"):
            qs = qs.filter(pre_launch=str(pre_launch).lower() in {"1", "true", "yes", "on"})
        if construction_status := self.request.query_params.get("construction_status"):
            qs = qs.filter(construction_status=construction_status)
        return qs

    def perform_create(self, serializer):
        serializer.save(company=getattr(self.request.user, "company", None))


class PropertyViewLogViewSet(viewsets.ModelViewSet):
    queryset = PropertyView.objects.select_related("property").all()
    serializer_class = PropertyViewSerializer
    permission_classes = [permissions.IsAuthenticated, FeatureActionPermission]
    feature_key = "crm.properties"

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PropertyMediaViewSet(viewsets.ModelViewSet):
    queryset = PropertyMedia.objects.select_related("property")
    serializer_class = PropertyMediaSerializer
    permission_classes = [permissions.IsAuthenticated, FeatureActionPermission]
    feature_key = "crm.properties"

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs
        company = getattr(user, "company", None)
        if company:
            return qs.filter(models.Q(property__company=company) | models.Q(property__company__isnull=True))
        return qs.filter(property__company__isnull=True)


class PropertyLocationViewSet(viewsets.ModelViewSet):
    queryset = PropertyLocation.objects.select_related("property")
    serializer_class = PropertyLocationSerializer
    permission_classes = [permissions.IsAuthenticated, FeatureActionPermission]
    feature_key = "crm.properties"

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs
        company = getattr(user, "company", None)
        if company:
            return qs.filter(models.Q(property__company=company) | models.Q(property__company__isnull=True))
        return qs.filter(property__company__isnull=True)


class PropertyImageViewSet(viewsets.ModelViewSet):
    queryset = PropertyImage.objects.select_related("property")
    serializer_class = PropertyImageSerializer
    permission_classes = [permissions.IsAuthenticated, FeatureActionPermission]
    feature_key = "crm.properties"

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs
        company = getattr(user, "company", None)
        if company:
            return qs.filter(models.Q(property__company=company) | models.Q(property__company__isnull=True))
        return qs.filter(property__company__isnull=True)

    def perform_create(self, serializer):
        image = serializer.save()
        PropertyMedia.objects.create(
            property=image.property,
            media_type=PropertyMedia.MediaType.IMAGE,
            file=image.image,
            external_url=image.image_url,
            caption=image.caption,
            sort_order=image.sort_order,
        )


class PropertyVideoViewSet(viewsets.ModelViewSet):
    queryset = PropertyVideo.objects.select_related("property")
    serializer_class = PropertyVideoSerializer
    permission_classes = [permissions.IsAuthenticated, FeatureActionPermission]
    feature_key = "crm.properties"

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs
        company = getattr(user, "company", None)
        if company:
            return qs.filter(models.Q(property__company=company) | models.Q(property__company__isnull=True))
        return qs.filter(property__company__isnull=True)

    def perform_create(self, serializer):
        video = serializer.save()
        PropertyMedia.objects.create(
            property=video.property,
            media_type=PropertyMedia.MediaType.VIDEO,
            file=video.video,
            external_url=video.video_url,
            caption=video.caption,
        )


class PropertyFeatureViewSet(viewsets.ModelViewSet):
    queryset = PropertyFeature.objects.select_related("property")
    serializer_class = PropertyFeatureSerializer
    permission_classes = [permissions.IsAuthenticated, FeatureActionPermission]
    feature_key = "crm.properties"

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs
        company = getattr(user, "company", None)
        if company:
            return qs.filter(models.Q(property__company=company) | models.Q(property__company__isnull=True))
        return qs.filter(property__company__isnull=True)


class FollowUpLeadViewSet(viewsets.ModelViewSet):
    queryset = FollowUp.objects.select_related("lead").all()
    serializer_class = FollowUpLeadSerializer
    permission_classes = [permissions.IsAuthenticated, FeatureActionPermission]
    feature_key = "crm.pipeline_deadlines"

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs
        role = (getattr(user, "role", "") or "").strip().lower()
        if role == "customer":
            return qs.filter(lead__converted_customer__user=user)
        if role in {"agent", "super_agent", "area_admin"}:
            return qs.filter(lead__assigned_agent__user=user)
        company = getattr(user, "company", None)
        return qs.filter(models.Q(lead__company=company) | models.Q(lead__company__isnull=True))


class LeadDocumentViewSet(viewsets.ModelViewSet):
    queryset = LeadDocument.objects.select_related("lead", "uploaded_by").all()
    serializer_class = LeadDocumentSerializer
    permission_classes = [permissions.IsAuthenticated, FeatureActionPermission]
    feature_key = "crm.leads"

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs
        role = (getattr(user, "role", "") or "").strip().lower()
        if role == "customer":
            return qs.filter(lead__converted_customer__user=user)
        if role in {"agent", "super_agent", "area_admin"}:
            return qs.filter(lead__assigned_agent__user=user)
        company = getattr(user, "company", None)
        return qs.filter(models.Q(lead__company=company) | models.Q(lead__company__isnull=True))

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)


class AgreementViewSet(viewsets.ModelViewSet):
    queryset = Agreement.objects.select_related("lead").all()
    serializer_class = AgreementSerializer
    permission_classes = [permissions.IsAuthenticated, FeatureActionPermission]
    feature_key = "crm.deals"

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs
        role = (getattr(user, "role", "") or "").strip().lower()
        if role == "customer":
            return qs.filter(lead__converted_customer__user=user)
        if role in {"agent", "super_agent", "area_admin"}:
            return qs.filter(lead__assigned_agent__user=user)
        company = getattr(user, "company", None)
        return qs.filter(models.Q(lead__company=company) | models.Q(lead__company__isnull=True))


class EMICalculatorAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from utils.emi import calculate_emi

        principal = float(request.query_params.get("amount", 0))
        rate = float(request.query_params.get("rate", 0))
        tenure = int(request.query_params.get("tenure", 0))
        return Response({"emi": calculate_emi(principal, rate, tenure)})


class FollowUpProcessorAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, FeatureActionPermission]
    feature_key = "crm.pipeline_deadlines"

    def post(self, request):
        process_due_followups()
        reassigned = reassign_stale_leads()
        created_followups = send_inactive_lead_followups()
        return Response(
            {
                "detail": "automation processed",
                "reassigned_leads": reassigned,
                "created_followups": created_followups,
            }
        )


class LeadImportPreviewAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if not (request.user.is_superuser or getattr(request.user, "is_staff", False)):
            raise PermissionDenied("Only admins can preview lead imports.")
        serializer = LeadCSVImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        preview = parse_lead_import_file(
            serializer.validated_data["file"],
            mapping=serializer.validated_data.get("mapping"),
            preview_limit=25,
        )
        return Response(
            {
                "detail": "preview ready",
                "file_type": preview["file_type"],
                "headers": preview["headers"],
                "preview_rows": preview["preview_rows"],
                "issues": preview["issues"],
                "total_rows": preview["total_rows"],
            }
        )


class LeadScrapeAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if not (request.user.is_superuser or getattr(request.user, "is_staff", False)):
            raise PermissionDenied("Only admins can scrape leads.")
        serializer = LeadScrapeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        raw_html = data.get("raw_html") or ""
        url = data.get("url") or "about:blank"
        if not raw_html and not data.get("url"):
            return Response({"detail": "url or raw_html is required"}, status=400)
        company = getattr(request.user, "company", None)
        source_config = resolve_source_config(
            company=company,
            source_key=data.get("source_key", ""),
            source_value=data.get("source", Lead.Source.WEB_SCRAPE),
        )
        batch, rows = scrape_leads_from_page(
            url=url,
            company=company,
            actor=request.user,
            source_config=source_config,
            auto_assign=data.get("auto_assign", True),
            max_items=data.get("max_items", 25),
            raw_html=raw_html,
        )
        return Response(
            {
                "detail": "scrape completed",
                "batch": LeadImportBatchSerializer(batch, context={"request": request}).data,
                "rows_extracted": len(rows),
            },
            status=status.HTTP_201_CREATED,
        )


class LeadCaptureAPIView(APIView):
    """
    Public-facing ingestion endpoint for ad/webhook sources.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token = (
            request.headers.get("X-AGENTFLOW-TOKEN")
            or request.query_params.get("token")
            or request.data.get("token")
            or ""
        )
        expected_token = getattr(settings, "SYNC_API_TOKEN", "")
        if expected_token and token != expected_token:
            return Response({"detail": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = LeadCaptureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        company = getattr(getattr(request, "user", None), "company", None) if getattr(getattr(request, "user", None), "is_authenticated", False) else None
        source_config = resolve_source_config(company=company, source_key=data.get("source_key", ""), source_value=data.get("source", Lead.Source.API))
        lead, _ = ingest_lead_payload(
            {
                "name": data.get("name"),
                "phone": data.get("phone"),
                "email": data.get("email"),
                "pincode": data.get("pincode"),
                "source": data.get("source", Lead.Source.API),
                "metadata": data.get("metadata", {}),
                "deal_value": data.get("deal_value") or 0,
                "stage": data.get("stage", Lead.Stage.NEW),
                "interest_type": data.get("interest_type", Lead.InterestType.BUY),
                "property_type": data.get("property_type", ""),
                "budget": data.get("budget"),
                "preferred_location": data.get("preferred_location", ""),
                "geo_location": data.get("geo_location", {}),
                "preferred_property_type": data.get("preferred_property_type", ""),
                "preferred_bedrooms": data.get("preferred_bedrooms"),
                "country": data.get("country", ""),
                "state": data.get("state", ""),
                "district": data.get("district", ""),
                "tehsil": data.get("tehsil", ""),
                "village": data.get("village", ""),
                "city": data.get("city", ""),
                "notes": data.get("notes", ""),
            },
            company=company,
            actor=request.user if getattr(request.user, "is_authenticated", False) else None,
            source_config=source_config,
            auto_assign=True,
        )
        return Response(LeadSerializer(lead).data, status=status.HTTP_201_CREATED)


class LeadWebhookAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, source_key: str):
        source = resolve_source_config(source_key=source_key)
        verify_token = request.query_params.get("hub.verify_token") or request.query_params.get("verify_token") or ""
        expected_token = getattr(source, "verify_token", "") or getattr(settings, "SYNC_API_TOKEN", "")
        if expected_token and verify_token == expected_token:
            return HttpResponse(request.query_params.get("hub.challenge") or request.query_params.get("challenge") or "")
        return Response({"detail": "verification failed"}, status=status.HTTP_401_UNAUTHORIZED)

    def post(self, request, source_key: str):
        source = resolve_source_config(source_key=source_key)
        payload = request.data
        rows = []
        if isinstance(payload, dict) and isinstance(payload.get("leads"), list):
            rows = payload.get("leads", [])
        elif isinstance(payload, dict) and isinstance(payload.get("data"), list):
            rows = payload.get("data", [])
        elif isinstance(payload, dict) and isinstance(payload.get("entry"), list):
            for entry in payload.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value") or {}
                    field_data = value.get("field_data") or []
                    row = {
                        "source": getattr(source, "source_value", Lead.Source.API),
                        "metadata": {"entry": entry, "change": change},
                    }
                    for field in field_data:
                        name = (field.get("name") or "").lower()
                        values = field.get("values") or []
                        value_text = values[0] if values else ""
                        if "phone" in name:
                            row["phone"] = value_text
                        elif "email" in name:
                            row["email"] = value_text
                        elif "city" in name:
                            row["city"] = value_text
                        elif "state" in name:
                            row["state"] = value_text
                        elif "budget" in name:
                            row["budget"] = value_text
                        elif "name" in name:
                            row["name"] = value_text
                        else:
                            row.setdefault("metadata", {})[name] = value_text
                    rows.append(row)
        elif isinstance(payload, dict):
            rows = [payload]

        batch = import_leads_from_rows(
            rows,
            company=getattr(getattr(request, "user", None), "company", None) if getattr(getattr(request, "user", None), "is_authenticated", False) else None,
            actor=request.user if getattr(request.user, "is_authenticated", False) else None,
            source_config=source,
            import_type=LeadImportBatch.ImportType.WEBHOOK,
            source_name=getattr(source, "name", source_key),
            auto_assign=True,
        )
        return Response(LeadImportBatchSerializer(batch).data, status=status.HTTP_202_ACCEPTED)


class LeadGeoAssignAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if not _is_admin_user(request.user):
            return Response({"detail": "Only admins can auto-assign by geo."}, status=status.HTTP_403_FORBIDDEN)
        lead_id = request.data.get("lead_id")
        if not lead_id:
            return Response({"detail": "lead_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        lead = get_object_or_404(Lead.objects.select_related("assigned_agent", "assigned_to", "company"), pk=lead_id)
        updated_fields = []
        for field in ("latitude", "longitude", "city", "state"):
            value = request.data.get(field)
            if value not in {None, ""}:
                setattr(lead, field, value)
                updated_fields.append(field)
        if updated_fields:
            lead.save(update_fields=[*updated_fields, "updated_at"])
        assign_lead_by_geo(lead, actor=request.user, reason=str(request.data.get("reason") or "Geo assignment via API"))
        return Response(LeadSerializer(lead, context={"request": request}).data)


class PhotoToLeadAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if not _is_admin_user(request.user):
            return Response({"detail": "Only admins can convert photos to leads."}, status=status.HTTP_403_FORBIDDEN)

        image = request.FILES.get("image") or request.data.get("image")
        raw_text = str(request.data.get("raw_text") or "").strip()
        create_lead = str(request.data.get("create_lead", "false")).strip().lower() in {"1", "true", "yes", "on"}
        source_key = str(request.data.get("source_key") or "").strip()
        source_value = str(request.data.get("source") or Lead.Source.API).strip() or Lead.Source.API
        source_config = resolve_source_config(company=getattr(request.user, "company", None), source_key=source_key, source_value=source_value)

        extracted = extract_lead_data_from_photo(upload=image, raw_text=raw_text, source=source_value)
        if not create_lead:
            return Response({"detail": "preview ready", "extracted": extracted})

        lead, _ = ingest_lead_payload(
            extracted,
            company=getattr(request.user, "company", None),
            actor=request.user,
            source_config=source_config,
            auto_assign=True,
        )
        return Response(
            {
                "detail": "lead created from photo",
                "extracted": extracted,
                "lead": LeadSerializer(lead, context={"request": request}).data,
            },
            status=status.HTTP_201_CREATED,
        )


class LeadLockAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        lead_id = request.data.get("lead_id")
        if not lead_id:
            return Response({"detail": "lead_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        lead = get_object_or_404(Lead.objects.select_related("assigned_agent", "assigned_to"), pk=lead_id)
        if not user_can_edit_lead(request.user, lead):
            return Response({"detail": "This lead is locked to another agent."}, status=status.HTTP_403_FORBIDDEN)
        lock_lead(lead, actor=request.user, reason=str(request.data.get("reason") or "Locked via API"))
        return Response(LeadSerializer(lead, context={"request": request}).data)


class LeadUnlockAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if not _is_admin_user(request.user):
            return Response({"detail": "Only admins can unlock leads."}, status=status.HTTP_403_FORBIDDEN)
        lead_id = request.data.get("lead_id")
        if not lead_id:
            return Response({"detail": "lead_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        lead = get_object_or_404(Lead.objects.select_related("assigned_agent", "assigned_to"), pk=lead_id)
        unlock_lead(lead, actor=request.user, reason=str(request.data.get("reason") or "Unlocked via API"))
        return Response(LeadSerializer(lead, context={"request": request}).data)
