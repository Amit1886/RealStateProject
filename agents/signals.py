from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import SaaSRole
from .models import Agent
from .wallet import AgentWallet


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_agent_profile(sender, instance, created, **kwargs):
    """
    Keep a 1:1 Agent row in sync whenever a user with an agent-capable role is created.
    We skip creation for non-agent roles but leave manual enablement possible from admin.
    """
    agent_roles = {SaaSRole.AGENT, SaaSRole.SUPER_AGENT, SaaSRole.AREA_ADMIN, SaaSRole.DISTRICT_ADMIN}
    if getattr(instance, "role", None) not in agent_roles:
        return
    Agent.objects.get_or_create(
        user=instance,
        defaults={
            "name": instance.get_full_name() or instance.username or instance.email,
            "phone": getattr(instance, "mobile", "") or "",
            "company": getattr(getattr(instance, "userprofile", None), "company", None),
        },
    )
    try:
        agent = instance.agent_profile
    except Agent.DoesNotExist:
        agent = None
    if agent:
        AgentWallet.objects.get_or_create(agent=agent)
