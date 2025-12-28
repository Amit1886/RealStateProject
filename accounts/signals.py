# accounts/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Sum

from .models import UserProfile
from billing.models import Plan
from khataapp.models import Transaction
from accounts.models import DailySummary

User = get_user_model()


# -------------------------------
# Auto-create UserProfile
# -------------------------------
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        free_plan = Plan.objects.filter(price=0).first()
        UserProfile.objects.get_or_create(
            user=instance,
            defaults={"plan": free_plan}
        )


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.userprofile.save()
    except UserProfile.DoesNotExist:
        free_plan = Plan.objects.filter(price=0).first()
        UserProfile.objects.create(user=instance, plan=free_plan)


# -------------------------------
# DAILY SUMMARY UPDATE
# -------------------------------
@receiver(post_save, sender=Transaction)
def update_daily_summary(sender, instance, created, **kwargs):

    if not created:
        return

    # PARTY MUST HAVE OWNER
    if not hasattr(instance.party, "owner"):
        return

    user = instance.party.owner
    today = timezone.now().date()

    # Get all today's transactions for this user
    txns = Transaction.objects.filter(
        party__owner=user,
        date=today
    )

    total_credit = txns.filter(txn_type="credit").aggregate(total=Sum("amount"))["total"] or 0
    total_debit = txns.filter(txn_type="debit").aggregate(total=Sum("amount"))["total"] or 0

    balance = total_debit - total_credit

    summary, _ = DailySummary.objects.get_or_create(
        user=user,
        date=today
    )

    summary.total_credit = total_credit
    summary.total_debit = total_debit
    summary.balance = balance
    summary.total_transactions = txns.count()

    summary.save()
