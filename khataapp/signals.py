# ~/myproject/khatapro/khataapp/signals.py
import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from django.contrib.auth import get_user_model

from khataapp.models import Transaction, CompanySettings, UserProfile
from khataapp.utils.credit_grade import compute_grade_for_party
from khataapp.utils.whatsapp_utils import send_whatsapp_message
from khataapp.utils.sms_utils import send_sms
from billing.models import Plan

logger = logging.getLogger(__name__)
User = get_user_model()


def _recalculate_and_save(party):
    """Recalculate and update party credit grade if changed (avoid recursion)."""
    try:
        new_grade = compute_grade_for_party(party)
        if party.credit_grade != new_grade:
            party.credit_grade = new_grade
            party.save(update_fields=["credit_grade"])
    except Exception as e:
        logger.exception(
            "Error recalculating grade for party %s: %s",
            getattr(party, "name", None),
            e,
        )


@receiver(post_save, sender=Transaction)
def handle_transaction_save(sender, instance, created, **kwargs):
    """On transaction save: send notifications & update grade."""
    party = instance.party

    # Auto notification setting check
    try:
        settings_obj = CompanySettings.objects.first()
        auto_notify = (
            getattr(settings_obj, "auto_send_messages", True)
            if settings_obj is not None
            else True
        )
    except Exception:
        auto_notify = True

    if created and auto_notify:
        msg = f"New Transaction: {party.name} - ₹{instance.amount} ({instance.txn_type})"

        # WhatsApp send
        number = (party.whatsapp_number or getattr(party, "mobile", "") or "").lstrip("+")
        if number:
            try:
                send_whatsapp_message(number, msg)
            except Exception:
                logger.exception("WhatsApp send failed for %s", getattr(party, "name", None))

        # SMS send
        number = (party.sms_number or getattr(party, "mobile", "") or "").lstrip("+")
        if number:
            try:
                send_sms(number, msg)
            except Exception:
                logger.exception("SMS send failed for %s", getattr(party, "name", None))

    # Always recalc grade after DB commit
    transaction.on_commit(lambda: _recalculate_and_save(party))


@receiver(post_delete, sender=Transaction)
def handle_transaction_delete(sender, instance, **kwargs):
    """On transaction delete: update grade."""
    transaction.on_commit(lambda: _recalculate_and_save(instance.party))


@receiver(post_save, sender=User)
def create_default_profile(sender, instance, created, **kwargs):
    """Create default UserProfile when new user registers."""
    if not created:
        return

    try:
        basic_plan = Plan.objects.filter(name__iexact="Basic").first()
    except Exception:
        basic_plan = None

    # Prevent duplicate profile
    try:
        if not UserProfile.objects.filter(user=instance).exists():
            UserProfile.objects.create(
                user=instance,
                plan=basic_plan,
                created_from="signup",
            )
    except Exception:
        logger.exception(
            "Failed to create UserProfile for user %s", getattr(instance, "username", None)
        )
