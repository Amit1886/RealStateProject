from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from addons.common.db import DB_EXCEPTIONS, db_unavailable
from addons.ai_call_assistant.models import CallSession
from addons.ai_call_assistant.services import process_ivr_input, queue_whatsapp_followup, start_call
from addons.common.permissions import IsStaffOrSuperuser


class CallSessionListAPI(APIView):
    permission_classes = [IsStaffOrSuperuser]

    def get(self, request):
        try:
            rows = CallSession.objects.order_by("-created_at")[:100]
            return Response(
                [
                    {
                        "id": row.id,
                        "caller_number": row.caller_number,
                        "status": row.status,
                        "intent": row.detected_intent,
                        "created_at": row.created_at,
                    }
                    for row in rows
                ]
            )
        except DB_EXCEPTIONS:
            return db_unavailable()


class CallStartAPI(APIView):
    permission_classes = [IsStaffOrSuperuser]

    def post(self, request):
        caller_number = request.data.get("caller_number")
        if not caller_number:
            return Response({"detail": "caller_number is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            session = start_call(
                caller_number=caller_number,
                branch_code=request.data.get("branch_code", "default"),
                language=request.data.get("language", "hi"),
            )
            return Response({"session_id": session.id, "status": session.status}, status=status.HTTP_201_CREATED)
        except DB_EXCEPTIONS:
            return db_unavailable()


class IVRInputAPI(APIView):
    permission_classes = [IsStaffOrSuperuser]

    def post(self, request, session_id: int):
        try:
            session = CallSession.objects.filter(id=session_id).first()
            if not session:
                return Response({"detail": "session not found"}, status=status.HTTP_404_NOT_FOUND)

            digit = str(request.data.get("digit", "")).strip()
            if not digit:
                return Response({"detail": "digit is required"}, status=status.HTTP_400_BAD_REQUEST)

            result = process_ivr_input(session, digit)
            return Response(result)
        except DB_EXCEPTIONS:
            return db_unavailable()


class FollowUpAPI(APIView):
    permission_classes = [IsStaffOrSuperuser]

    def post(self, request, session_id: int):
        try:
            session = CallSession.objects.filter(id=session_id).first()
            if not session:
                return Response({"detail": "session not found"}, status=status.HTTP_404_NOT_FOUND)

            message = request.data.get("message") or "Thank you for calling us."
            followup = queue_whatsapp_followup(session, message=message)
            return Response({"followup_id": followup.id, "status": followup.status})
        except DB_EXCEPTIONS:
            return db_unavailable()
