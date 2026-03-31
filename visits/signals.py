from django.db.models.signals import post_save
from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import SiteVisit
from utils.geo import calculate_distance
from leads.pipeline import record_visit_no_show
from leads.services import send_whatsapp_or_notify


@receiver(pre_save, sender=SiteVisit)
def cache_old_visit_flags(sender, instance: SiteVisit, **kwargs):
    if not instance.pk:
        instance._old_is_no_show = False
        instance._old_status = None
        return
    old = SiteVisit.objects.filter(pk=instance.pk).values("is_no_show", "status").first()
    instance._old_is_no_show = bool(old.get("is_no_show")) if old else False
    instance._old_status = old.get("status") if old else None


@receiver(post_save, sender=SiteVisit)
def update_agent_visit_count(sender, instance: SiteVisit, created: bool, **kwargs):
    if created and instance.agent_id:
        try:
            instance.agent.record_visit()
        except Exception:
            pass
        # WhatsApp reminder to customer if number exists
        lead = instance.lead
        if lead.mobile:
            send_whatsapp_or_notify(
                lead.mobile,
                f"Your site visit is scheduled on {instance.visit_date:%Y-%m-%d %H:%M} at {instance.location}.",
                fallback_user=lead.assigned_to,
            )

    if instance.is_no_show and not getattr(instance, "_old_is_no_show", False):
        try:
            record_visit_no_show(instance.lead, penalty=10)
        except Exception:
            pass
    elif instance.status == SiteVisit.Status.COMPLETED and getattr(instance, "_old_status", None) != SiteVisit.Status.COMPLETED:
        try:
            lead = instance.lead
            lead.reliability_score = min(100, int(lead.reliability_score or 0) + 2)
            lead.save(update_fields=["reliability_score", "updated_at"])
        except Exception:
            pass

    # distance check
    if instance.checkin_latitude and instance.checkin_longitude and instance.visit_latitude and instance.visit_longitude:
        dist = calculate_distance(
            instance.visit_latitude,
            instance.visit_longitude,
            instance.checkin_latitude,
            instance.checkin_longitude,
        )
        if dist is not None:
            instance.distance_mismatch = dist
            # mark suspicious if > 0.5km
            if dist > 0.5:
                try:
                    from agents.models import AgentRiskProfile

                    rp, _ = AgentRiskProfile.objects.get_or_create(agent=instance.agent)
                    rp.risk_score = max(rp.risk_score, 70)
                    rp.risk_level = AgentRiskProfile.RiskLevel.HIGH
                    rp.save(update_fields=["risk_score", "risk_level"])
                except Exception:
                    pass
        SiteVisit.objects.filter(pk=instance.pk).update(distance_mismatch=dist)
        instance.distance_mismatch = dist
