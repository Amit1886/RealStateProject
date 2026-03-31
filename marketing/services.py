from __future__ import annotations

from django.db import models, transaction
from django.utils import timezone

from event_bus.publish import publish_event
from leads.models import Lead
from marketing.models import Campaign, CampaignMessage


def _company_from_user(user):
    return getattr(getattr(user, "userprofile", None), "company", None)


def generate_ad_copy(*, objective: str, product: str, language: str = "en") -> str:
    """
    Minimal safe generator (no external calls).
    Replace with OpenAI/other providers in ai_engine later.
    """

    objective = (objective or "promote").strip()
    product = (product or "your product").strip()
    if language == "hi":
        return f"{product} के लिए {objective} अभियान शुरू करें। अभी संपर्क करें!"
    return f"Start your {objective} campaign for {product}. Contact us today!"


def _audience_queryset(*, campaign: Campaign):
    """
    Audience filters (initial):
    - status (lead status list)
    - pincode (pincode id)
    - assigned_to (user id)
    """

    q = Lead.objects.filter(company=campaign.company)
    audience = campaign.audience or {}
    statuses = audience.get("lead_status")
    if statuses:
        q = q.filter(status__in=statuses)
    pincode_id = audience.get("pincode")
    if pincode_id:
        q = q.filter(pincode_id=pincode_id)
    assigned_to_id = audience.get("assigned_to")
    if assigned_to_id:
        q = q.filter(assigned_to_id=assigned_to_id)
    return q


@transaction.atomic
def start_campaign(*, campaign: Campaign, actor=None) -> Campaign:
    if campaign.status not in {Campaign.Status.DRAFT, Campaign.Status.SCHEDULED}:
        return campaign

    campaign.mark_running()
    leads = _audience_queryset(campaign=campaign).only("id", "mobile", "email")
    created = 0
    for lead in leads.iterator(chunk_size=500):
        destination = lead.mobile or lead.email or ""
        msg = CampaignMessage.objects.create(
            campaign=campaign,
            lead=lead,
            destination=destination,
            payload={"copy": campaign.ad_copy},
        )
        publish_event(
            topic="marketing",
            event_type="campaign.message.created",
            payload={"campaign_id": campaign.id, "message_id": msg.id, "channel": campaign.channel},
            owner=actor,
            key=str(msg.id),
        )
        created += 1

    campaign.recipients_total = created
    campaign.save(update_fields=["recipients_total", "updated_at"])
    return campaign


@transaction.atomic
def mark_message_sent(message: CampaignMessage, *, provider_ref: str = ""):
    if message.status == CampaignMessage.Status.SENT:
        return message
    message.status = CampaignMessage.Status.SENT
    message.provider_ref = (provider_ref or "")[:120]
    message.sent_at = timezone.now()
    message.save(update_fields=["status", "provider_ref", "sent_at"])
    Campaign.objects.filter(id=message.campaign_id).update(recipients_sent=models.F("recipients_sent") + 1)
    return message


@transaction.atomic
def mark_message_failed(message: CampaignMessage, *, error: str = ""):
    if message.status == CampaignMessage.Status.FAILED:
        return message
    message.status = CampaignMessage.Status.FAILED
    message.last_error = (error or "")[:2000]
    message.save(update_fields=["status", "last_error"])
    Campaign.objects.filter(id=message.campaign_id).update(recipients_failed=models.F("recipients_failed") + 1)
    return message

