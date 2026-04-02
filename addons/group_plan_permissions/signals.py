from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from billing.models import Plan


def _resolve_group_plan(user):
    return (
        Plan.objects.filter(active=True, groups__id__in=user.groups.values_list("id", flat=True))
        .distinct()
        .order_by("-price_monthly", "-price_yearly", "-price", "-id")
        .first()
    )


@receiver(user_logged_in)
def apply_group_plan_to_profile(sender, request, user, **kwargs):
    """If a user has no explicit UserProfile.plan, fill it from group->plan mapping."""
    try:
        from accounts.models import UserProfile

        profile = UserProfile.objects.filter(user=user).select_related("plan").first()
        if not profile:
            return
        if profile.plan_id:
            return

        plan = _resolve_group_plan(user)
        if not plan:
            return

        profile.plan = plan
        profile.save(update_fields=["plan", "updated_at"])
    except Exception:
        # Never block login on permission sync.
        return
