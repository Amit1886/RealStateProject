from datetime import timedelta

from django.utils import timezone

from addons.ai_call_assistant.models import CallLog, CallSession, WhatsAppFollowUp
from addons.ai_call_assistant.tasks import send_whatsapp_followup


def start_call(caller_number: str, branch_code: str = "default", language: str = "hi") -> CallSession:
    session = CallSession.objects.create(
        caller_number=caller_number,
        branch_code=branch_code,
        language=language,
        status=CallSession.Status.IN_PROGRESS,
    )
    CallLog.objects.create(session=session, event_type="call_started", payload={"language": language})
    return session


def process_ivr_input(session: CallSession, digit: str) -> dict:
    intent_map = {
        "1": "rate_enquiry",
        "2": "book_order",
        "3": "speak_agent",
    }
    intent = intent_map.get(digit, "unknown")
    session.detected_intent = intent
    session.save(update_fields=["detected_intent", "updated_at"])
    CallLog.objects.create(session=session, event_type="ivr_input", payload={"digit": digit, "intent": intent})
    return {"intent": intent}


def sync_crm(session: CallSession) -> None:
    # Safe placeholder for external CRM sync. Keeps legacy CRM untouched.
    session.crm_synced = True
    session.save(update_fields=["crm_synced", "updated_at"])
    CallLog.objects.create(session=session, event_type="crm_sync", payload={"status": "ok"})


def queue_whatsapp_followup(session: CallSession, message: str, after_minutes: int = 5) -> WhatsAppFollowUp:
    followup = WhatsAppFollowUp.objects.create(
        session=session,
        message=message,
        scheduled_for=timezone.now() + timedelta(minutes=after_minutes),
    )
    send_whatsapp_followup.delay(followup.id)
    return followup
