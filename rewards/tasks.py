from __future__ import annotations

from celery import shared_task
from django.contrib.auth import get_user_model

from rewards.services import award_daily_login_reward, award_lead_conversion_reward, award_signup_bonus, ensure_default_reward_rules, process_referral_for_user

User = get_user_model()


@shared_task
def ensure_reward_defaults_task():
    ensure_default_reward_rules()


@shared_task
def grant_signup_bonus_task(user_id: int):
    user = User.objects.filter(pk=user_id).first()
    if not user:
        return None
    return award_signup_bonus(user)


@shared_task
def process_referral_reward_task(user_id: int):
    user = User.objects.filter(pk=user_id).first()
    if not user:
        return None
    return process_referral_for_user(user)


@shared_task
def grant_daily_login_reward_task(user_id: int):
    user = User.objects.filter(pk=user_id).first()
    if not user:
        return None
    return award_daily_login_reward(user)


@shared_task
def grant_lead_conversion_reward_task(lead_id: int):
    from leads.models import Lead

    lead = Lead.objects.select_related("assigned_agent", "assigned_agent__user").filter(pk=lead_id).first()
    if not lead:
        return None
    return award_lead_conversion_reward(lead)
