from decimal import Decimal

from django.db.models.signals import post_save
from django.dispatch import receiver

from deals.models import Deal
from deals.services import settle_deal_commission
from leads.models import Lead
from leads.services import send_whatsapp_or_notify


@receiver(post_save, sender=Lead)
def create_deal_on_close(sender, instance: Lead, created: bool, **kwargs):
    # Create a deal record when lead is closed and has a value.
    if created:
        return
    if instance.status != Lead.Status.CLOSED:
        return
    amount = Decimal(str(instance.deal_value or 0))
    if amount <= 0 or not instance.assigned_agent_id:
        return

    deal, _ = Deal.objects.get_or_create(
        lead=instance,
        defaults={
            "agent": instance.assigned_agent,
            "property": instance.interested_property,
            "company": instance.company,
            "deal_amount": amount,
            "commission_rate": Decimal("2.00"),
            "commission_amount": amount * Decimal("0.02"),  # default 2% commission
            "status": Deal.Status.WON,
            "stage": Deal.Stage.CLOSED,
            "closing_date": instance.updated_at.date() if instance.updated_at else None,
        },
    )
    # Ensure agent references align
    if deal.agent_id != instance.assigned_agent_id:
        deal.agent = instance.assigned_agent
        deal.save(update_fields=["agent"])

    if deal.commission_amount > 0:
        settle_deal_commission(deal, settled=False, credit_agent_wallet=False, note=f"Lead {instance.id}")
    # WhatsApp notify customer
    if instance.mobile:
        send_whatsapp_or_notify(
            instance.mobile,
            f"Great news! Your deal is closed. Amount: {deal.deal_amount}. Thank you.",
            fallback_user=instance.assigned_to,
        )
