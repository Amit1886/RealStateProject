from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from addons.common.db import DB_EXCEPTIONS, db_unavailable
from addons.common.permissions import IsStaffOrSuperuser
from addons.autopilot_engine.models import AutopilotEvent, FeatureToggle, WorkflowRule
from addons.autopilot_engine.services.event_bus import publish_event


class FeatureToggleListAPI(APIView):
    permission_classes = [IsStaffOrSuperuser]

    def get(self, request):
        try:
            rows = FeatureToggle.objects.order_by("key").values("id", "key", "enabled", "description")
            return Response(list(rows))
        except DB_EXCEPTIONS:
            return db_unavailable()


class FeatureToggleUpdateAPI(APIView):
    permission_classes = [IsStaffOrSuperuser]

    def post(self, request, pk: int):
        try:
            toggle = FeatureToggle.objects.filter(id=pk).first()
            if not toggle:
                return Response({"detail": "toggle not found"}, status=status.HTTP_404_NOT_FOUND)

            toggle.enabled = bool(request.data.get("enabled", toggle.enabled))
            toggle.save(update_fields=["enabled", "updated_at"])
            return Response({"id": toggle.id, "enabled": toggle.enabled})
        except DB_EXCEPTIONS:
            return db_unavailable()


class EmitEventAPI(APIView):
    permission_classes = [IsStaffOrSuperuser]

    def post(self, request):
        event_key = request.data.get("event_key")
        payload = request.data.get("payload") or {}
        branch_code = request.data.get("branch_code", "default")

        if not event_key:
            return Response({"detail": "event_key is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            event = publish_event(
                event_key=event_key,
                payload=payload,
                branch_code=branch_code,
                source="manual_api",
                actor=request.user,
            )
            return Response({"event_id": event.id, "status": event.status}, status=status.HTTP_202_ACCEPTED)
        except DB_EXCEPTIONS:
            return db_unavailable()


class RuleListAPI(APIView):
    permission_classes = [IsStaffOrSuperuser]

    def get(self, request):
        try:
            rows = WorkflowRule.objects.prefetch_related("actions").order_by("event_key", "priority")
            data = []
            for row in rows:
                data.append(
                    {
                        "id": row.id,
                        "name": row.name,
                        "event_key": row.event_key,
                        "is_active": row.is_active,
                        "priority": row.priority,
                        "branch_code": row.branch_code,
                        "actions": [
                            {
                                "id": action.id,
                                "action_key": action.action_key,
                                "run_order": action.run_order,
                                "critical": action.critical,
                            }
                            for action in row.actions.all()
                        ],
                    }
                )
            return Response(data)
        except DB_EXCEPTIONS:
            return db_unavailable()


class ExecutionListAPI(APIView):
    permission_classes = [IsStaffOrSuperuser]

    def get(self, request):
        try:
            events = AutopilotEvent.objects.order_by("-created_at")[:100]
            return Response(
                [
                    {
                        "id": event.id,
                        "event_key": event.event_key,
                        "status": event.status,
                        "attempts": event.attempts,
                        "max_attempts": event.max_attempts,
                        "last_error": event.last_error,
                        "created_at": event.created_at,
                    }
                    for event in events
                ]
            )
        except DB_EXCEPTIONS:
            return db_unavailable()
