from datetime import timedelta

from django.conf import settings
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from leads.models import Lead
from leads.pipeline import STAGE_MAX_DURATIONS
from leads.services import auto_assign_lead, schedule_followup, send_whatsapp_or_notify
from ai.scoring_engine import compute_lead_score, recommend_best_agent
from payouts.services import create_payout_for_lead
from payouts.wallet_system import credit_on_lead_close
from rewards.services import evaluate_rewards_for_agent
from rewards.tasks import grant_lead_conversion_reward_task
from realtime.services.publisher import publish_event
from voice.services import build_lead_qualification_script, start_voice_call
from voice.models import VoiceCall


@receiver(pre_save, sender=Lead)
def cache_old_values(sender, instance: Lead, **kwargs):
    if not instance.pk:
        instance._old_status = None
        instance._old_stage = None
        return
    old = Lead.objects.filter(pk=instance.pk).values("status", "lead_score", "temperature", "stage").first()
    instance._old_status = old["status"] if old else None
    instance._old_score = old.get("lead_score") if old else None
    instance._old_temp = old.get("temperature") if old else None
    instance._old_stage = old.get("stage") if old else None


@receiver(post_save, sender=Lead)
def publish_lead_events(sender, instance: Lead, created: bool, **kwargs):
    now = timezone.now()
    if created or getattr(instance, "_old_stage", None) != instance.stage or not instance.stage_updated_at:
        stage_updated_at = instance.stage_updated_at or now
        stage_deadline = (
            stage_updated_at + STAGE_MAX_DURATIONS.get(instance.stage, timedelta(0))
            if instance.stage in STAGE_MAX_DURATIONS
            else None
        )
        Lead.objects.filter(pk=instance.pk).update(
            stage_updated_at=stage_updated_at,
            stage_deadline=stage_deadline,
            is_overdue=False,
        )
        instance.stage_updated_at = stage_updated_at
        instance.stage_deadline = stage_deadline
        instance.is_overdue = False

    # Ensure brand-new leads are auto-assigned even when created outside DRF viewsets.
    if created and not instance.assigned_agent_id:
        auto_assign_lead(lead=instance)
        schedule_followup(instance, message=f"Hi {instance.name or 'there'}, we found properties in your budget. Want to schedule a visit?")
        # WhatsApp notify if number present
        if instance.mobile:
            send_whatsapp_or_notify(instance.mobile, f"Hi {instance.name or 'there'}, thanks for your interest. We'll call soon.", fallback_user=instance.assigned_to)

    # Auto scoring
    score, temp = compute_lead_score(instance)
    if score != instance.lead_score or temp != instance.temperature:
        Lead.objects.filter(pk=instance.pk).update(lead_score=score, temperature=temp)
        instance.lead_score = score
        instance.temperature = temp

    payload = {
        "id": instance.id,
        "name": instance.name,
        "mobile": instance.mobile,
        "email": instance.email,
        "status": instance.status,
        "score": instance.score,
        "assigned_to": instance.assigned_to_id,
        "assigned_agent": instance.assigned_agent_id,
        "source": instance.source,
        "created_at": instance.created_at.isoformat(),
    }
    event_type = "lead.created" if created else "lead.updated"
    publish_event("leads_live", event_type, payload)

    # Trigger AI voice call on new leads (best-effort, non-blocking)
    try:
        if created:
            start_voice_call(
                instance,
                trigger=VoiceCall.Trigger.NEW_LEAD,
                script=build_lead_qualification_script(instance),
            )
    except Exception:
        # Do not break lead save flow
        pass

    # Trigger payout + reward pipeline on closure
    try:
        if not created and instance.status == Lead.Status.CLOSED and getattr(instance, "_old_status", None) != Lead.Status.CLOSED:
            if instance.assigned_agent_id:
                try:
                    instance.assigned_agent.record_closure(instance.deal_value)
                except Exception:
                    pass
                create_payout_for_lead(instance)
                evaluate_rewards_for_agent(instance.assigned_agent)
                credit_on_lead_close(instance)
                if getattr(settings, "DISABLE_CELERY", False):
                    grant_lead_conversion_reward_task.run(instance.pk)
                else:
                    grant_lead_conversion_reward_task.delay(instance.pk)
    except Exception:
        pass

    # AI recommendation for best agent (stored in metadata)
    try:
        best_agent = recommend_best_agent(instance)
        if best_agent and instance.assigned_agent_id != best_agent.id:
            meta = instance.metadata or {}
            meta["recommended_agent_id"] = best_agent.id
            Lead.objects.filter(pk=instance.pk).update(metadata=meta)
    except Exception:
        pass
