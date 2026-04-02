from __future__ import annotations

import json
import logging
from typing import Any

from django.db import models
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_POST

from core_settings.models import SettingDefinition, SettingValue
from core_settings.services import sync_settings_registry
from leads.models import Lead
from voice.command_parser import parse_voice_command
from voice.models import VoiceCall, VoiceCallTurn, VoiceCommand
from voice.serializers import VoiceCallSerializer, VoiceCallTurnSerializer
from voice.services import apply_voice_qualification, build_lead_qualification_script, start_voice_call
from whatsapp.message_handler import execute_parsed_command

logger = logging.getLogger(__name__)


def _get_global_setting(key: str, default: Any = "") -> Any:
    try:
        sync_settings_registry()
    except Exception:
        pass
    try:
        definition = SettingDefinition.objects.filter(key=key).first()
        if not definition:
            return default
        value_obj = SettingValue.objects.filter(definition=definition, owner__isnull=True).first()
        return value_obj.value if value_obj else definition.default_value
    except Exception:
        return default


@login_required
def voice_dashboard(request):
    if not bool(_get_global_setting("ai_tools_enabled", True)) or not bool(_get_global_setting("voice_enabled", True)):
        return render(request, "voice/disabled.html", {})
    recent = VoiceCommand.objects.filter(owner=request.user).order_by("-created_at")[:30]
    return render(request, "voice/dashboard.html", {"recent": recent})


def _redirect_for_reference(reference_type: str, reference_id: int | None) -> str:
    if not reference_type or not reference_id:
        return ""
    try:
        if reference_type == "commerce.Order":
            return reverse("commerce:order_detail", kwargs={"pk": reference_id})
        if reference_type == "accounts.Expense":
            return reverse("accounts:expense_list")
        if reference_type == "khataapp.Transaction":
            return reverse("accounts:expense_list")
    except Exception:
        return ""
    return ""


@login_required
@require_POST
def api_voice_command(request):
    if not bool(_get_global_setting("ai_tools_enabled", True)) or not bool(_get_global_setting("voice_enabled", True)):
        return JsonResponse({"ok": False, "error": "Voice accounting is disabled"}, status=403)
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)

    text = str(payload.get("text") or "").strip()
    if not text:
        return JsonResponse({"ok": False, "error": "Empty text"}, status=400)

    cmd = VoiceCommand.objects.create(owner=request.user, raw_text=text, status=VoiceCommand.Status.RECEIVED)
    parsed = parse_voice_command(text)
    if not parsed:
        cmd.status = VoiceCommand.Status.FAILED
        cmd.error = "Unrecognized command"
        cmd.save(update_fields=["status", "error"])
        return JsonResponse({"ok": False, "error": "Unrecognized command"})

    cmd.parsed_intent = parsed.intent
    cmd.parsed_payload = parsed.payload
    cmd.status = VoiceCommand.Status.PARSED
    cmd.save(update_fields=["parsed_intent", "parsed_payload", "status"])

    try:
        res = execute_parsed_command(owner=request.user, parsed=parsed)
        cmd.status = VoiceCommand.Status.CREATED if res.ok else VoiceCommand.Status.FAILED
        cmd.reference_type = res.reference_type
        cmd.reference_id = res.reference_id
        cmd.error = "" if res.ok else res.reply
        cmd.save(update_fields=["status", "reference_type", "reference_id", "error"])
        return JsonResponse(
            {
                "ok": res.ok,
                "reply": res.reply,
                "intent": res.intent,
                "reference_type": res.reference_type,
                "reference_id": res.reference_id,
                "redirect_url": _redirect_for_reference(res.reference_type, res.reference_id),
            }
        )
    except Exception as e:
        logger.exception("Voice command execution failed")
        cmd.status = VoiceCommand.Status.FAILED
        cmd.error = f"{type(e).__name__}: {e}"
        cmd.save(update_fields=["status", "error"])
        return JsonResponse({"ok": False, "error": "Failed to execute command"}, status=500)


class VoiceCallViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = VoiceCall.objects.select_related("lead", "agent").prefetch_related("turns")
    serializer_class = VoiceCallSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or getattr(user, "is_staff", False):
            return qs
        return qs.filter(models.Q(agent=user) | models.Q(lead__created_by=user)).distinct()

    @action(detail=True, methods=["post"])
    def qualify(self, request, pk=None):
        call = self.get_object()
        call = apply_voice_qualification(
            call,
            transcript=str(request.data.get("transcript") or ""),
            responses=request.data.get("responses") or {},
            recording_url=str(request.data.get("recording_url") or ""),
        )
        return Response(self.get_serializer(call).data)


class VoiceCallTurnViewSet(viewsets.ModelViewSet):
    queryset = VoiceCallTurn.objects.select_related("call")
    serializer_class = VoiceCallTurnSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or getattr(user, "is_staff", False):
            return qs
        return qs.filter(models.Q(call__agent=user) | models.Q(call__lead__created_by=user)).distinct()


class VoiceLeadCallAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        lead_id = request.data.get("lead")
        lead = Lead.objects.filter(id=lead_id).first()
        if not lead:
            return Response({"detail": "Lead not found"}, status=status.HTTP_404_NOT_FOUND)
        call = start_voice_call(
            lead,
            trigger=VoiceCall.Trigger.MANUAL,
            script=str(request.data.get("script_prompt") or build_lead_qualification_script(lead)),
            language=str(request.data.get("language") or "auto"),
        )
        return Response(VoiceCallSerializer(call, context={"request": request}).data, status=status.HTTP_201_CREATED)
