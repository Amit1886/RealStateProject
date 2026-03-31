from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from billing.permissions import FeatureActionPermission
from .models import GroupVisit, GroupVisitAttendance, SiteVisit
from .serializers import GroupVisitAttendanceSerializer, GroupVisitSerializer, SiteVisitSerializer


class SiteVisitViewSet(viewsets.ModelViewSet):
    queryset = SiteVisit.objects.select_related("lead", "agent")
    serializer_class = SiteVisitSerializer
    permission_classes = [permissions.IsAuthenticated, FeatureActionPermission]
    feature_key = "crm.visits"

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs
        # Agents see their visits
        return qs.filter(agent__user=user)

    def perform_create(self, serializer):
        visit = serializer.save()
        # Update lead stage to visit when a visit is scheduled
        lead = visit.lead
        target_stage = getattr(lead.Stage, "VISIT_SCHEDULED", lead.Stage.VISIT)
        if lead.stage != target_stage:
            lead.stage = target_stage
            lead.save(update_fields=["stage", "updated_at"])
        return visit


class GroupVisitViewSet(viewsets.ModelViewSet):
    queryset = GroupVisit.objects.select_related("agent", "created_by").prefetch_related("leads")
    serializer_class = GroupVisitSerializer
    permission_classes = [permissions.IsAuthenticated, FeatureActionPermission]
    feature_key = "crm.group_visits"

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs
        return qs.filter(agent__user=user)

    @action(detail=True, methods=["post"])
    def mark_attendance(self, request, pk=None):
        group_visit = self.get_object()
        lead_id = request.data.get("lead")
        status_value = request.data.get("attendance_status") or "present"
        if not lead_id:
            return Response({"detail": "lead is required"}, status=400)
        attendance, _ = GroupVisitAttendance.objects.get_or_create(group_visit=group_visit, lead_id=lead_id)
        attendance.attendance_status = status_value
        if status_value == GroupVisitAttendance.AttendanceStatus.PRESENT:
            attendance.checked_in_at = attendance.checked_in_at or timezone.now()
        attendance.remarks = request.data.get("remarks") or attendance.remarks
        attendance.save()
        return Response(GroupVisitAttendanceSerializer(attendance, context={"request": request}).data)


class GroupVisitAttendanceViewSet(viewsets.ModelViewSet):
    queryset = GroupVisitAttendance.objects.select_related("group_visit", "lead")
    serializer_class = GroupVisitAttendanceSerializer
    permission_classes = [permissions.IsAuthenticated, FeatureActionPermission]
    feature_key = "crm.group_visits"

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return qs
        return qs.filter(group_visit__agent__user=user)
