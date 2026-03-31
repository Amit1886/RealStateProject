from django.db import models
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import SaaSRole
from intelligence.models import (
    AggregatedProperty,
    DemandHeatmapSnapshot,
    InvestorMatch,
    InvestorProfile,
    LeadPurchase,
    PremiumLeadListing,
    PriceTrendSnapshot,
    PropertyAlertSubscription,
    PropertyImportBatch,
    RealEstateDocument,
)
from intelligence.serializers import (
    AggregatedPropertySerializer,
    DemandHeatmapSnapshotSerializer,
    InvestorMatchSerializer,
    InvestorProfileSerializer,
    LeadPurchaseSerializer,
    PremiumLeadListingSerializer,
    PriceTrendSnapshotSerializer,
    PropertyAlertSubscriptionSerializer,
    PropertyImportBatchSerializer,
    RealEstateDocumentSerializer,
)
from intelligence.services import (
    ingest_aggregated_listing,
    purchase_lead_listing,
    refresh_demand_heatmap,
    refresh_investor_matches_for_project,
    refresh_investor_matches_for_property,
    refresh_price_trends,
)
from intelligence.tasks import run_property_import_batch_task
from leads.models import Lead, Property, PropertyProject


class _CompanyScopedMixin:
    def _company(self):
        return getattr(self.request.user, "company", None)


class PropertyImportBatchViewSet(_CompanyScopedMixin, viewsets.ModelViewSet):
    queryset = PropertyImportBatch.objects.all()
    serializer_class = PropertyImportBatchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or getattr(user, "is_staff", False):
            return qs
        return qs.filter(models.Q(company=self._company()) | models.Q(company__isnull=True))

    def perform_create(self, serializer):
        serializer.save(company=self._company())

    @action(detail=True, methods=["post"])
    def run(self, request, pk=None):
        batch = self.get_object()
        try:
            run_property_import_batch_task.delay(batch.id)  # type: ignore[attr-defined]
        except Exception:
            run_property_import_batch_task(batch.id)
        return Response({"detail": "import scheduled", "batch_id": batch.id}, status=status.HTTP_202_ACCEPTED)


class AggregatedPropertyViewSet(_CompanyScopedMixin, viewsets.ReadOnlyModelViewSet):
    queryset = AggregatedProperty.objects.select_related("import_batch", "matched_property", "duplicate_of")
    serializer_class = AggregatedPropertySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or getattr(user, "is_staff", False):
            return qs
        return qs.filter(models.Q(company=self._company()) | models.Q(company__isnull=True))


class ManualAggregationAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        payloads = request.data.get("records") or []
        results = []
        company = getattr(request.user, "company", None)
        for payload in payloads:
            agg = ingest_aggregated_listing(payload, company=company)
            results.append(AggregatedPropertySerializer(agg, context={"request": request}).data)
        return Response({"count": len(results), "results": results}, status=status.HTTP_201_CREATED)


class DemandHeatmapSnapshotViewSet(_CompanyScopedMixin, viewsets.ReadOnlyModelViewSet):
    queryset = DemandHeatmapSnapshot.objects.all()
    serializer_class = DemandHeatmapSnapshotSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        city = self.request.query_params.get("city")
        district = self.request.query_params.get("district")
        if city:
            qs = qs.filter(city__iexact=city)
        if district:
            qs = qs.filter(district__iexact=district)
        user = self.request.user
        if user.is_superuser or getattr(user, "is_staff", False):
            return qs
        return qs.filter(models.Q(company=self._company()) | models.Q(company__isnull=True))

    @action(detail=False, methods=["post"])
    def refresh(self, request):
        snapshots = refresh_demand_heatmap(company=self._company())
        return Response({"count": len(snapshots)})


class PriceTrendSnapshotViewSet(_CompanyScopedMixin, viewsets.ReadOnlyModelViewSet):
    queryset = PriceTrendSnapshot.objects.all()
    serializer_class = PriceTrendSnapshotSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if property_type := self.request.query_params.get("property_type"):
            qs = qs.filter(property_type=property_type)
        if city := self.request.query_params.get("city"):
            qs = qs.filter(city__iexact=city)
        if user.is_superuser or getattr(user, "is_staff", False):
            return qs
        return qs.filter(models.Q(company=self._company()) | models.Q(company__isnull=True))

    @action(detail=False, methods=["post"])
    def refresh(self, request):
        rows = refresh_price_trends(company=self._company())
        return Response({"count": len(rows)})


class InvestorProfileViewSet(_CompanyScopedMixin, viewsets.ModelViewSet):
    queryset = InvestorProfile.objects.all()
    serializer_class = InvestorProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or getattr(user, "is_staff", False):
            return qs
        return qs.filter(models.Q(user=user) | models.Q(company=self._company()))

    def perform_create(self, serializer):
        serializer.save(
            user=serializer.validated_data.get("user") or self.request.user,
            company=self._company(),
            email=serializer.validated_data.get("email") or self.request.user.email,
            phone=serializer.validated_data.get("phone") or self.request.user.mobile,
            name=serializer.validated_data.get("name") or (self.request.user.get_full_name() or self.request.user.email),
        )


class InvestorMatchViewSet(_CompanyScopedMixin, viewsets.ReadOnlyModelViewSet):
    queryset = InvestorMatch.objects.select_related("investor", "property", "project")
    serializer_class = InvestorMatchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or getattr(user, "is_staff", False):
            return qs
        return qs.filter(models.Q(investor__user=user) | models.Q(investor__company=self._company()))

    @action(detail=False, methods=["post"])
    def refresh(self, request):
        total = 0
        for property_obj in Property.objects.exclude(status=Property.Status.REJECTED).order_by("-created_at")[:100]:
            total += len(refresh_investor_matches_for_property(property_obj))
        for project in PropertyProject.objects.filter(approved=True).order_by("-created_at")[:100]:
            total += len(refresh_investor_matches_for_project(project))
        return Response({"matches_created_or_updated": total})


class PropertyAlertSubscriptionViewSet(_CompanyScopedMixin, viewsets.ModelViewSet):
    queryset = PropertyAlertSubscription.objects.select_related("customer", "customer__user")
    serializer_class = PropertyAlertSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or getattr(user, "is_staff", False):
            return qs
        return qs.filter(customer__user=user)

    def perform_create(self, serializer):
        from customers.models import Customer

        customer = getattr(self.request.user, "customer_profile", None)
        if not customer:
            customer, _ = Customer.objects.get_or_create(
                user=self.request.user,
                defaults={"company": self._company()},
            )
        serializer.save(customer=customer, company=self._company())


class PremiumLeadListingViewSet(_CompanyScopedMixin, viewsets.ModelViewSet):
    queryset = PremiumLeadListing.objects.select_related("lead", "buyer_agent", "seller")
    serializer_class = PremiumLeadListingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or getattr(user, "is_staff", False):
            return qs
        role = getattr(user, "role", "")
        if role in {SaaSRole.AGENT, SaaSRole.SUPER_AGENT}:
            return qs.filter(models.Q(company=self._company()) | models.Q(company__isnull=True))
        return qs.filter(seller=user)

    def perform_create(self, serializer):
        serializer.save(company=self._company(), seller=self.request.user)

    @action(detail=True, methods=["post"])
    def purchase(self, request, pk=None):
        listing = self.get_object()
        buyer_agent = getattr(request.user, "agent_profile", None)
        if not buyer_agent:
            return Response({"detail": "Agent profile required"}, status=400)
        try:
            purchase = purchase_lead_listing(listing, buyer_agent=buyer_agent, actor_user=request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(LeadPurchaseSerializer(purchase, context={"request": request}).data, status=status.HTTP_201_CREATED)


class LeadPurchaseViewSet(_CompanyScopedMixin, viewsets.ReadOnlyModelViewSet):
    queryset = LeadPurchase.objects.select_related("listing", "lead", "buyer_agent")
    serializer_class = LeadPurchaseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or getattr(user, "is_staff", False):
            return qs
        return qs.filter(buyer_agent__user=user)


class RealEstateDocumentViewSet(_CompanyScopedMixin, viewsets.ModelViewSet):
    queryset = RealEstateDocument.objects.select_related("uploaded_by", "property", "lead", "deal", "customer", "agent", "project", "builder")
    serializer_class = RealEstateDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or getattr(user, "is_staff", False):
            return qs
        return qs.filter(
            models.Q(uploaded_by=user)
            | models.Q(customer__user=user)
            | models.Q(agent__user=user)
            | models.Q(property__owner=user)
        )

    def perform_create(self, serializer):
        serializer.save(company=self._company(), uploaded_by=self.request.user)


class IntelligenceDashboardAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        company = getattr(request.user, "company", None)
        heatmap_qs = DemandHeatmapSnapshot.objects.filter(company=company)
        heatmaps = heatmap_qs.order_by("-snapshot_date", "-hot_investment_score")[:5]
        trends = PriceTrendSnapshot.objects.filter(company=company).order_by("-snapshot_date", "-price_change_percent")[:5]
        top_agents = list(
            Lead.objects.filter(company=company, status=Lead.Status.CLOSED)
            .values("assigned_agent__name")
            .annotate(closed=models.Count("id"), revenue=models.Sum("deal_value"))
            .order_by("-closed")[:5]
        )
        from marketing.models import Campaign

        campaign_performance = list(
            Campaign.objects.filter(models.Q(company=company) | models.Q(company__isnull=True))
            .values("name", "channel", "status")
            .annotate(sent=models.Sum("recipients_sent"), failed=models.Sum("recipients_failed"))
            .order_by("-sent")[:5]
        )
        return Response(
            {
                "heatmap": DemandHeatmapSnapshotSerializer(heatmaps, many=True).data,
                "price_trends": PriceTrendSnapshotSerializer(trends, many=True).data,
                "top_agents": top_agents,
                "top_investment_areas": DemandHeatmapSnapshotSerializer(heatmap_qs.order_by("-hot_investment_score")[:5], many=True).data,
                "campaign_performance": campaign_performance,
            }
        )
