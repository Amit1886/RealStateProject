from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import models

from agents.models import Agent
from crm.models import CallLog, CustomerNote, CustomerProfile, FollowUp
from crm.serializers import CallLogSerializer, CustomerNoteSerializer, CustomerProfileSerializer, FollowUpSerializer
from crm.heatmap import heatmap_points
from crm.marketplace import list_marketplace
from crm.live_map import live_map_data
from crm.performance import agent_stats, build_leaderboard, sync_agent_score


class _CompanyScopedMixin:
    def _company(self):
        return getattr(self.request.user, "company", None) or getattr(getattr(self.request.user, "userprofile", None), "company", None)

    def scope_queryset(self, qs):
        user = self.request.user
        if user.is_superuser:
            return qs
        company = self._company()
        if qs.model is CustomerProfile:
            return qs.filter(company=company)
        if qs.model is CallLog:
            return qs.filter(
                models.Q(customer__company=company)
                | models.Q(lead__created_by__userprofile__company=company)
                | models.Q(lead__assigned_to__userprofile__company=company)
            ).distinct()
        return qs.filter(customer__company=company)


class CustomerProfileViewSet(_CompanyScopedMixin, viewsets.ModelViewSet):
    queryset = CustomerProfile.objects.all()
    serializer_class = CustomerProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.scope_queryset(super().get_queryset())

    def perform_create(self, serializer):
        company = self._company()
        serializer.save(company=company)


class CustomerNoteViewSet(_CompanyScopedMixin, viewsets.ModelViewSet):
    queryset = CustomerNote.objects.select_related("customer", "author")
    serializer_class = CustomerNoteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.scope_queryset(super().get_queryset())

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class CallLogViewSet(_CompanyScopedMixin, viewsets.ModelViewSet):
    queryset = CallLog.objects.select_related("customer", "agent")
    serializer_class = CallLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.scope_queryset(super().get_queryset())

    def perform_create(self, serializer):
        lead = serializer.validated_data.get("lead")
        customer = serializer.validated_data.get("customer")
        phone_number = serializer.validated_data.get("phone_number") or ""
        if not phone_number and lead:
            phone_number = lead.mobile
        if not phone_number and customer:
            phone_number = getattr(getattr(customer, "user", None), "mobile", "")
        call = serializer.save(agent=self.request.user, phone_number=phone_number)
        if call.lead_id:
            from leads.models import LeadActivity

            LeadActivity.objects.create(
                lead=call.lead,
                actor=self.request.user,
                activity_type="call",
                note=(call.note or call.outcome or "Call logged")[:500],
                payload={
                    "direction": call.direction,
                    "duration_seconds": call.duration_seconds,
                    "missed_call": call.missed_call,
                    "recording_url": call.recording_url,
                },
            )


class FollowUpViewSet(_CompanyScopedMixin, viewsets.ModelViewSet):
    queryset = FollowUp.objects.select_related("customer", "owner")
    serializer_class = FollowUpSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.scope_queryset(super().get_queryset())

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        obj = self.get_object()
        obj.mark_done()
        return Response(FollowUpSerializer(obj, context={"request": request}).data)


class HeatmapAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        points = heatmap_points(
            {
                "city": request.query_params.get("city"),
                "property_type": request.query_params.get("property_type"),
                "since": request.query_params.get("since"),
            }
        )
        return Response({"points": points})


class MarketplaceAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({"projects": list_marketplace(approved_only=True)})


class LiveMapAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        minutes = int(request.query_params.get("minutes", 15))
        return Response(live_map_data(minutes=minutes))


class LeaderboardAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        days = int(request.query_params.get("days", 7))
        limit = int(request.query_params.get("limit", 20))
        data = build_leaderboard(days=days, limit=limit)
        return Response({"days": days, "results": data})


class AgentStatsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        agent_id = request.query_params.get("agent_id")
        agent = None
        if agent_id:
            agent = Agent.objects.filter(id=agent_id).first()
        if agent is None and hasattr(request.user, "agent_profile"):
            agent = request.user.agent_profile
        if agent is None and request.user.is_superuser:
            agent = Agent.objects.order_by("-updated_at").first()
        if agent is None:
            return Response({"detail": "agent not found"}, status=404)
        days = int(request.query_params.get("days", 30))
        score = sync_agent_score(agent)
        return Response({**agent_stats(agent, days=days), "latest_score": score.points, "latest_score_date": str(score.score_date)})
