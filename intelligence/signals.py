from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from intelligence.services import (
    dispatch_builder_launch_alert,
    dispatch_property_alerts_for_property,
    evaluate_fake_agent,
    evaluate_spam_lead,
    refresh_investor_matches_for_project,
    refresh_investor_matches_for_property,
)
from leads.models import Lead, Property, PropertyProject
from agents.models import Agent


@receiver(post_save, sender=Property)
def intelligence_on_property_create(sender, instance: Property, created: bool, **kwargs):
    try:
        refresh_investor_matches_for_property(instance)
    except Exception:
        pass
    if created:
        try:
            dispatch_property_alerts_for_property(instance, trigger="new_property")
        except Exception:
            pass


@receiver(pre_save, sender=Property)
def cache_old_property_price(sender, instance: Property, **kwargs):
    if not instance.pk:
        instance._old_price = None
        return
    old = Property.objects.filter(pk=instance.pk).values("price").first()
    instance._old_price = old["price"] if old else None


@receiver(post_save, sender=Property)
def intelligence_on_property_price_change(sender, instance: Property, created: bool, **kwargs):
    old_price = getattr(instance, "_old_price", None)
    if created or old_price in (None, instance.price):
        return
    try:
        dispatch_property_alerts_for_property(instance, trigger="price_drop")
    except Exception:
        pass


@receiver(post_save, sender=PropertyProject)
def intelligence_on_project_create(sender, instance: PropertyProject, created: bool, **kwargs):
    try:
        refresh_investor_matches_for_project(instance)
    except Exception:
        pass
    if created:
        try:
            dispatch_builder_launch_alert(instance)
        except Exception:
            pass


@receiver(post_save, sender=Lead)
def intelligence_on_lead_save(sender, instance: Lead, created: bool, **kwargs):
    if not created:
        return
    try:
        evaluate_spam_lead(instance)
    except Exception:
        pass


@receiver(post_save, sender=Agent)
def intelligence_on_agent_save(sender, instance: Agent, created: bool, **kwargs):
    try:
        evaluate_fake_agent(instance)
    except Exception:
        pass
