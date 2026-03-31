from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver

from rewards.services import get_or_create_reward_coin
from rewards.tasks import (
    ensure_reward_defaults_task,
    grant_daily_login_reward_task,
    grant_signup_bonus_task,
    process_referral_reward_task,
)

User = get_user_model()


def _run_task(task, *args):
    if getattr(settings, "DISABLE_CELERY", False):
        return task.run(*args)
    return task.delay(*args)


@receiver(post_migrate)
def bootstrap_reward_defaults(sender, **kwargs):
    _run_task(ensure_reward_defaults_task)


@receiver(post_save, sender=User)
def setup_user_reward_account(sender, instance, created, **kwargs):
    get_or_create_reward_coin(instance)
    if instance.is_active:
        _run_task(grant_signup_bonus_task, instance.pk)
        if instance.referred_by_id:
            _run_task(process_referral_reward_task, instance.pk)


@receiver(user_logged_in)
def reward_daily_login(sender, user, request, **kwargs):
    _run_task(grant_daily_login_reward_task, user.pk)
