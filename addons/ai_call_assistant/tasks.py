from celery import shared_task
from django.utils import timezone

from addons.ai_call_assistant.models import CallLog, WhatsAppFollowUp


@shared_task
def send_whatsapp_followup(followup_id: int):
    followup = WhatsAppFollowUp.objects.filter(id=followup_id).first()
    if not followup:
        return

    if followup.scheduled_for > timezone.now():
        return

    followup.status = WhatsAppFollowUp.Status.SENT
    followup.provider_message_id = f"wa-{followup.id}"
    followup.save(update_fields=["status", "provider_message_id"])
    CallLog.objects.create(
        session=followup.session,
        event_type="whatsapp_followup_sent",
        payload={"followup_id": followup.id},
    )
