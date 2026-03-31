from __future__ import annotations

import logging
import os
from datetime import timedelta
from typing import Optional

import requests
from django.conf import settings
from django.db import models
from django.utils import timezone

from leads.models import Lead
from leads.services import auto_assign_lead
from voice.models import VoiceCall

logger = logging.getLogger(__name__)


def _voice_enabled() -> bool:
    return bool(getattr(settings, "VOICE_AI_ENABLED", True))


def _use_async_voice() -> bool:
    return not getattr(settings, "RUNNING_TESTS", False) and not getattr(settings, "DISABLE_CELERY", False)


def _twilio_credentials() -> tuple[str, str, str]:
    return (
        os.getenv("TWILIO_ACCOUNT_SID") or "",
        os.getenv("TWILIO_AUTH_TOKEN") or "",
        os.getenv("TWILIO_FROM_NUMBER") or "",
    )


def start_voice_call(lead: Lead, *, trigger: VoiceCall.Trigger, script: str = "", language: str = "auto") -> VoiceCall:
    """
    Fire-and-forget helper that records intent and kicks off provider request.
    The actual provider request is best executed via Celery; if Celery is absent we
    still attempt a synchronous HTTP call with tight timeouts.
    """
    call = VoiceCall.objects.create(
        lead=lead,
        agent=lead.assigned_to,
        trigger=trigger,
        status=VoiceCall.Status.PENDING,
        script_prompt=script[:4000],
        language=language or "auto",
    )

    if not _voice_enabled():
        call.mark_failed("voice_ai_disabled")
        return call

    # Prefer Celery if available
    try:
        from voice.tasks import dispatch_voice_call

        if _use_async_voice():
            dispatch_voice_call.delay(call.id)
            return call
        dispatch_voice_call(call.id)
        return call
    except Exception:
        pass

    # Fallback: make a lightweight provider request synchronously (best effort)
    _execute_provider_call(call)
    return call


def build_lead_qualification_script(lead: Lead) -> str:
    return (
        "Ask the lead three questions in a natural tone: "
        "1. Are you looking to buy or sell property? "
        "2. Which location are you interested in? "
        "3. What is your budget range? "
        f"Lead context: {lead.name or lead.mobile}, source={lead.source}."
    )


def schedule_inactive_lead_calls(days: int = 2) -> int:
    """
    Scan for leads that have been inactive and trigger a call.
    Returns number of calls scheduled.
    """
    cutoff = timezone.now() - timedelta(days=days)
    qs = Lead.objects.filter(status__in=["new", "warm", "hot", "contacted"]).filter(
        (models.Q(last_contacted_at__lt=cutoff) | models.Q(last_contacted_at__isnull=True))
    )
    total = 0
    for lead in qs[:200]:  # guardrail
        start_voice_call(lead, trigger=VoiceCall.Trigger.INACTIVE_LEAD)
        total += 1
    return total


def apply_voice_qualification(
    call: VoiceCall,
    *,
    transcript: str = "",
    responses: dict | None = None,
    recording_url: str = "",
):
    responses = responses or {}
    lead = call.lead
    if transcript:
        call.transcript = transcript[:5000]
    if recording_url:
        call.recording_url = recording_url
    call.structured_response = responses
    call.summary = (
        f"Intent={responses.get('intent') or responses.get('buy_or_sell')}, "
        f"location={responses.get('location')}, budget={responses.get('budget')}"
    )[:2000]

    buy_or_sell = str(responses.get("buy_or_sell") or responses.get("intent") or "").strip().lower()
    location = str(responses.get("location") or "").strip()
    budget = responses.get("budget")
    interested = str(responses.get("interested") or "yes").strip().lower() not in {"no", "false", "0"}
    if buy_or_sell:
        lead.metadata = {**(lead.metadata or {}), "voice_buy_or_sell": buy_or_sell}
    if location:
        lead.preferred_location = location[:160]
        if not lead.city:
            lead.city = location[:120]
    if budget:
        try:
            lead.budget = budget
        except Exception:
            pass
    if interested:
        lead.status = Lead.Status.QUALIFIED
        lead.stage = Lead.Stage.QUALIFIED
        call.qualified = True
        call.qualification_status = "qualified"
        if not lead.assigned_agent_id:
            auto_assign_lead(lead=lead)
    else:
        call.qualification_status = "not_interested"
    lead.save(update_fields=["metadata", "preferred_location", "city", "budget", "status", "stage", "updated_at"])
    call.status = VoiceCall.Status.COMPLETED
    call.completed_at = timezone.now()
    call.save(
        update_fields=[
            "transcript",
            "structured_response",
            "summary",
            "recording_url",
            "qualified",
            "qualification_status",
            "status",
            "completed_at",
            "updated_at",
        ]
    )
    return call


def _execute_provider_call(call: VoiceCall) -> Optional[str]:
    """
    Minimal Twilio / Exotel hook. In production, move to Celery + provider SDKs.
    """
    acc_sid, auth_token, from_number = _twilio_credentials()
    if not (acc_sid and auth_token and from_number):
        call.mark_failed("twilio_credentials_missing")
        return None

    try:
        # Very small Twilio-compatible REST request (no SDK dependency).
        url = f"https://api.twilio.com/2010-04-01/Accounts/{acc_sid}/Calls.json"
        to_number = call.lead.mobile
        payload = {
            "To": to_number,
            "From": from_number,
            "Url": os.getenv("TWILIO_VOICE_WEBHOOK") or "",  # should host dynamic TwiML built from script_prompt
        }
        resp = requests.post(url, data=payload, auth=(acc_sid, auth_token), timeout=6)
        if resp.ok:
            data = resp.json()
            call.provider = "twilio"
            call.provider_call_id = data.get("sid", "")
            call.status = VoiceCall.Status.DIALING
            call.started_at = timezone.now()
            call.save(update_fields=["provider", "provider_call_id", "status", "started_at", "updated_at"])
            return call.provider_call_id
        call.mark_failed(f"provider_error:{resp.status_code}")
    except Exception as exc:
        logger.warning("Voice provider call failed: %s", exc)
        call.mark_failed(str(exc))
    return None
