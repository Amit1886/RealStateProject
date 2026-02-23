from django.db.models.signals import post_save
from django.dispatch import receiver

from addons.ai_call_assistant.models import CallSession
from addons.common.eventing import publish_event_safe


@receiver(post_save, sender=CallSession)
def call_session_events(sender, instance, created, **kwargs):
    event_key = "call_session_created" if created else "call_session_updated"
    publish_event_safe(
        event_key=event_key,
        payload={
            "session_id": instance.id,
            "caller_number": instance.caller_number,
            "intent": instance.detected_intent,
            "status": instance.status,
        },
        branch_code=instance.branch_code,
        source="ai_call_assistant",
    )
