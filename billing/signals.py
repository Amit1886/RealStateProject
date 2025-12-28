# billing/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Subscription, Plan
from khataapp.models import UserProfile
from .models import OrderItem

@receiver(post_save, sender=Subscription)
def apply_subscription_groups(sender, instance: Subscription, created, **kwargs):
    """
    When a subscription is created or updated, make sure user's groups include the plan.groups.
    Also remove plan-groups that are no longer provided by any active subscription for that user.
    """
    user = instance.user

    # collect groups that should be present (union of groups from all active subscriptions)
    active_subs = Subscription.objects.filter(user=user, status="active").select_related("plan")
    allowed_groups = set()
    for s in active_subs:
        for g in s.plan.groups.all():
            allowed_groups.add(g)

    # add allowed groups
    for g in allowed_groups:
        user.groups.add(g)

    # remove groups that belong to any Plan but are not in allowed_groups
    all_plan_groups = set()
    for p in Plan.objects.all():
        for g in p.groups.all():
            all_plan_groups.add(g)

    for g in all_plan_groups:
        if g not in allowed_groups and g in user.groups.all():
            # only remove plan-owned groups (do not touch unrelated groups)
            user.groups.remove(g)


@receiver(post_delete, sender=Subscription)
def remove_subscription_groups_on_delete(sender, instance: Subscription, **kwargs):
    """
    When a subscription is deleted, recompute allowed groups and remove plan-groups not allowed anymore.
    """
    user = instance.user

    # FIX: use status="active" instead of active=True
    active_subs = Subscription.objects.filter(user=user, status="active").select_related("plan")
    allowed_groups = set()
    for s in active_subs:
        for g in s.plan.groups.all():
            allowed_groups.add(g)

    all_plan_groups = set()
    for p in Plan.objects.all():
        for g in p.groups.all():
            all_plan_groups.add(g)

    for g in all_plan_groups:
        if g not in allowed_groups and g in user.groups.all():
            user.groups.remove(g)

@receiver(post_save, sender=Subscription)
def update_user_profile_plan(sender, instance, **kwargs):
    profile, created = UserProfile.objects.get_or_create(user=instance.user)
    if instance.plan and instance.status == "active":
        profile.plan = instance.plan
        profile.save()

@receiver(post_save, sender=OrderItem)
def update_order_total_on_save(sender, instance, **kwargs):
    order = instance.order
    order.update_total()
    order.save()

@receiver(post_delete, sender=OrderItem)
def update_order_total_on_delete(sender, instance, **kwargs):
    order = instance.order
    order.update_total()
    order.save()