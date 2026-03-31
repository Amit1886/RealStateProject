from __future__ import annotations

import csv
import html
import io
import re
import zipfile
from datetime import timedelta, timezone as dt_timezone
from decimal import Decimal
from xml.etree import ElementTree as ET
from typing import Iterable, Sequence

import requests
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.text import slugify

from accounts.models import SaaSRole
from agents.models import Agent
from agents.services import (
    agents_for_city,
    agents_for_district,
    agents_for_pincode,
    agents_for_state,
    agents_for_tehsil,
    agents_for_village,
    nearest_agents,
    pick_agent_round_robin,
)
from communication.models import EmailLog, MessageLog, SMSLog
from communication.services import log_email, log_message, log_sms, queue_notification_event
from deals.models import Deal, Payment
from deals.models_commission import Commission
from leads.models import (
    FollowUp,
    Lead,
    LeadActivity,
    LeadAssignment,
    LeadAssignmentLog,
    LeadImportBatch,
    LeadSource,
)
from notifications.services import notify_user
from visits.models import SiteVisit


def _normalize_text(value) -> str:
    return str(value or "").strip()


def _normalize_phone(value) -> str:
    raw = "".join(ch for ch in str(value or "") if ch.isdigit())
    if len(raw) >= 10:
        return raw[-15:]
    return raw


def _normalize_email(value) -> str:
    return str(value or "").strip().lower()


def _active_assignment_response_deadline() -> timezone.datetime:
    return timezone.now() + timedelta(hours=2)


def _agent_distance_score(agent: Agent, lead: Lead) -> float:
    lead_lat = lead.latitude or lead.geo_location.get("lat") or lead.geo_location.get("latitude")
    lead_lng = lead.longitude or lead.geo_location.get("lng") or lead.geo_location.get("longitude")
    agent_lat = agent.current_latitude or agent.last_latitude
    agent_lng = agent.current_longitude or agent.last_longitude
    if None in {lead_lat, lead_lng, agent_lat, agent_lng}:
        return 10_000.0
    try:
        return abs(float(lead_lat) - float(agent_lat)) + abs(float(lead_lng) - float(agent_lng))
    except Exception:
        return 10_000.0


def _best_candidate(candidates: Sequence[Agent], lead: Lead) -> Agent | None:
    candidates = [candidate for candidate in candidates if candidate and candidate.is_active and not candidate.is_blocked]
    if not candidates:
        return None

    loads = (
        Lead.objects.filter(assigned_agent__in=candidates)
        .exclude(status__in=[Lead.Status.CLOSED, Lead.Status.LOST, Lead.Status.CONVERTED])
        .values("assigned_agent")
        .annotate(c=Count("id"))
    )
    load_map = {row["assigned_agent"]: row["c"] for row in loads}

    def _score(agent: Agent):
        return (
            load_map.get(agent.id, 0),
            -int(agent.performance_score or 0),
            _agent_distance_score(agent, lead),
            agent.last_assigned_at or timezone.datetime(1970, 1, 1, tzinfo=dt_timezone.utc),
        )

    return sorted(candidates, key=_score)[0]


def _coerce_float(value):
    try:
        if value in {None, ""}:
            return None
        return float(value)
    except Exception:
        return None


def _extract_phone_from_text(text: str) -> str:
    phones = []
    for match in PHONE_RE.findall(text or ""):
        phone = _normalize_phone(match)
        if phone:
            phones.append(phone)
    return phones[0] if phones else ""


def _extract_email_from_text(text: str) -> str:
    emails = []
    for match in EMAIL_RE.findall(text or ""):
        email = _normalize_email(match)
        if email:
            emails.append(email)
    return emails[0] if emails else ""


def _extract_name_from_text(text: str) -> str:
    lines = [re.sub(r"\s+", " ", line).strip(" :-") for line in (text or "").splitlines()]
    for line in lines:
        if not line:
            continue
        lowered = line.lower()
        if "@" in line or any(ch.isdigit() for ch in line):
            continue
        if any(token in lowered for token in ("phone", "mobile", "email", "www", "http", "whatsapp")):
            continue
        if len(line) > 80:
            continue
        return line[:160]
    return ""


def _ocr_text_from_image(upload) -> str:
    raw_bytes = _read_upload_bytes(upload)
    if not raw_bytes:
        return ""
    try:
        from PIL import Image
        import pytesseract
    except Exception:
        return ""
    try:
        image = Image.open(io.BytesIO(raw_bytes))
        return pytesseract.image_to_string(image) or ""
    except Exception:
        return ""


def extract_lead_data_from_photo(*, upload=None, raw_text: str = "", source: str = Lead.Source.API) -> dict:
    text = (raw_text or "").strip()
    if not text and upload is not None:
        text = _ocr_text_from_image(upload).strip()
    name = _extract_name_from_text(text)
    phone = _extract_phone_from_text(text)
    email = _extract_email_from_text(text)
    if not any([name, phone, email]):
        raise ValueError("No lead data could be extracted from the provided image or text.")
    metadata = {
        "extracted_text": text[:5000],
        "extraction_mode": "raw_text" if raw_text else "ocr" if upload is not None else "manual",
    }
    return {
        "name": name,
        "phone": phone,
        "email": email,
        "source": source or Lead.Source.API,
        "notes": "Photo to lead extraction",
        "metadata": metadata,
    }


def lock_lead(lead: Lead, *, agent: Agent | None = None, actor=None, reason: str = "") -> Lead:
    now = timezone.now()
    agent = agent or lead.assigned_agent
    lead.is_locked = True
    lead.locked_by = agent
    lead.locked_at = now
    lead.lock_reason = (reason or "Locked for assigned agent")[:255]
    lead.save(update_fields=["is_locked", "locked_by", "locked_at", "lock_reason", "updated_at"])
    LeadActivity.objects.create(
        lead=lead,
        actor=actor,
        activity_type="lock",
        note=lead.lock_reason,
        payload={"agent_id": getattr(agent, "id", None)},
    )
    return lead


def unlock_lead(lead: Lead, *, actor=None, reason: str = "") -> Lead:
    lead.is_locked = False
    lead.locked_by = None
    lead.locked_at = None
    lead.lock_reason = (reason or "")[:255]
    lead.save(update_fields=["is_locked", "locked_by", "locked_at", "lock_reason", "updated_at"])
    LeadActivity.objects.create(
        lead=lead,
        actor=actor,
        activity_type="unlock",
        note=lead.lock_reason or "Unlocked",
        payload={},
    )
    return lead


def user_can_edit_lead(user, lead: Lead) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
        return True
    role = (getattr(user, "role", "") or "").strip().lower()
    if role in {"admin", "super_admin", "state_admin", "district_admin", "area_admin"}:
        return True
    if lead.assigned_agent_id and getattr(getattr(lead.assigned_agent, "user", None), "id", None) == getattr(user, "id", None):
        return True
    if lead.assigned_to_id and lead.assigned_to_id == getattr(user, "id", None):
        return True
    return False


def assign_lead_by_geo(lead: Lead, *, actor=None, reason: str = ""):
    company = lead.company
    latitude = _coerce_float(lead.latitude or lead.geo_location.get("lat") or lead.geo_location.get("latitude"))
    longitude = _coerce_float(lead.longitude or lead.geo_location.get("lng") or lead.geo_location.get("longitude"))
    if latitude is not None and longitude is not None:
        nearest = nearest_agents(latitude, longitude, company=company, limit=10)
        chosen = _best_candidate(nearest, lead)
        if chosen:
            return assign_lead(
                lead,
                agent=chosen,
                actor=actor,
                reason=reason or "Geo-assigned to nearest available agent",
                match_level="nearest",
                assignment_type=LeadAssignmentLog.AssignmentType.AUTO,
            )

    pool = Agent.objects.filter(
        is_active=True,
        is_blocked=False,
        approval_status=Agent.ApprovalStatus.APPROVED,
    )
    if company:
        pool = pool.filter(Q(company=company) | Q(company__isnull=True))
    chosen = _best_candidate(pool, lead)
    if chosen:
        return assign_lead(
            lead,
            agent=chosen,
            actor=actor,
            reason=reason or "Geo fallback to least-loaded agent",
            match_level="fallback",
            assignment_type=LeadAssignmentLog.AssignmentType.AUTO,
        )
    return lead


def resolve_source_config(*, company=None, source_key: str = "", source_value: str = "") -> LeadSource | None:
    source_key = _normalize_text(source_key)
    source_value = _normalize_text(source_value)
    if source_key:
        source = LeadSource.objects.filter(slug=source_key, is_active=True).filter(
            Q(company=company) | Q(company__isnull=True)
        ).first()
        if source:
            return source
    if source_value:
        return LeadSource.objects.filter(source_value=source_value, is_active=True).filter(
            Q(company=company) | Q(company__isnull=True)
        ).order_by("-company_id", "name").first()
    return None


def find_duplicate_lead(*, company=None, phone: str = "", email: str = "") -> Lead | None:
    phone = _normalize_phone(phone)
    email = _normalize_email(email)
    query = Q()
    if phone:
        query |= Q(mobile=phone)
    if email:
        query |= Q(email=email)
    if not query:
        return None
    qs = Lead.objects.filter(query)
    if company:
        qs = qs.filter(Q(company=company) | Q(company__isnull=True))
    return qs.order_by("-created_at").first()


def mark_assignment_responded(lead: Lead, *, actor=None, when=None):
    when = when or timezone.now()
    assignment = lead.assignments.filter(is_active=True).order_by("-created_at").first()
    if assignment and not assignment.first_contact_at:
        assignment.first_contact_at = when
        assignment.save(update_fields=["first_contact_at", "updated_at"])
    if not lead.agent_first_response_at:
        lead.agent_first_response_at = when
        lead.save(update_fields=["agent_first_response_at", "updated_at"])
    if actor:
        LeadActivity.objects.create(
            lead=lead,
            actor=actor,
            activity_type="agent_response",
            note="Agent responded to lead",
            payload={"assignment_id": getattr(assignment, "id", None)},
        )
    if assignment and assignment.agent_id:
        try:
            from crm.performance import sync_agent_score

            sync_agent_score(assignment.agent)
        except Exception:
            pass


@transaction.atomic
def assign_lead(
    lead: Lead,
    *,
    agent: Agent | None = None,
    actor=None,
    reason: str = "",
    match_level: str = "",
    assignment_type: str = LeadAssignmentLog.AssignmentType.AUTO,
):
    if not agent:
        return lead

    now = timezone.now()
    previous_agent_id = lead.assigned_agent_id
    lead.assignments.filter(is_active=True).exclude(agent=agent).update(is_active=False, released_at=now, updated_at=now)

    assignment = lead.assignments.filter(agent=agent, is_active=True).order_by("-created_at").first()
    if not assignment:
        assignment = LeadAssignment.objects.create(
            lead=lead,
            agent=agent,
            assigned_by=actor,
            assignment_type=assignment_type,
            matched_on=match_level or "",
            reason=(reason or "")[:300],
            response_due_at=_active_assignment_response_deadline(),
            payload={"actor_id": getattr(actor, "id", None)},
        )

    lead.assigned_agent = agent
    lead.assigned_to = agent.user
    lead.assigned_at = now
    if match_level:
        lead.distribution_level = match_level
    if reason:
        lead.distribution_reason = reason[:200]
    if previous_agent_id and previous_agent_id != agent.id:
        lead.last_reassigned_at = now
    lead.is_locked = True
    lead.locked_by = agent
    lead.locked_at = now
    lead.lock_reason = (reason or "Locked for assigned agent")[:255]
    lead.save(
        update_fields=[
            "assigned_agent",
            "assigned_to",
            "assigned_at",
            "distribution_level",
            "distribution_reason",
            "last_reassigned_at",
            "is_locked",
            "locked_by",
            "locked_at",
            "lock_reason",
            "updated_at",
        ]
    )
    LeadActivity.objects.create(
        lead=lead,
        actor=actor,
        activity_type="assign",
        note=(reason or "")[:500],
        payload={"assigned_agent": getattr(agent, "id", None), "assignment_id": assignment.id},
    )
    LeadAssignmentLog.objects.create(
        lead=lead,
        agent=agent,
        assigned_by=actor,
        assignment_type=assignment_type,
        matched_on=match_level or "",
        note=(reason or "")[:300],
        payload={
            "agent_id": getattr(agent, "id", None),
            "agent_user_id": getattr(getattr(agent, "user", None), "id", None),
            "assignment_id": assignment.id,
        },
    )
    agent.bump_last_assigned()
    _refresh_agent_metrics(agent)
    try:
        from crm.performance import sync_agent_score

        sync_agent_score(agent)
    except Exception:
        pass

    try:
        if agent.user:
            notify_user(
                user=agent.user,
                title="New lead assigned",
                body=f"{lead.name or lead.mobile} assigned to you.",
                level="info",
                data={"lead_id": lead.id},
            )
            queue_notification_event(
                users=[agent.user],
                title="New lead assigned",
                body=f"{lead.name or lead.mobile} assigned to you.",
                lead=lead,
                channels=["in_app", "email", "whatsapp"],
                email=getattr(agent.user, "email", ""),
                whatsapp_number=getattr(agent, "phone", ""),
                sender=actor,
                metadata={"lead_id": lead.id, "assignment_type": assignment_type, "assignment_id": assignment.id},
            )
    except Exception:
        pass
    return lead


def auto_assign_lead(*, lead: Lead, fallback_agent: Agent | None = None, fallback_user=None, exclude_agent_ids=None):
    if lead.assigned_agent_id or lead.assigned_to_id:
        return lead

    company = lead.company
    exclude_agent_ids = set(exclude_agent_ids or [])
    pincode_value = (getattr(getattr(lead, "pincode", None), "code", None) or lead.pincode_text or "").strip()
    district_value = _normalize_text(
        lead.district or getattr(getattr(getattr(lead, "pincode", None), "district", None), "name", "")
    )
    state_value = _normalize_text(
        lead.state
        or getattr(getattr(getattr(getattr(lead, "pincode", None), "district", None), "state", None), "name", "")
    )
    city_value = _normalize_text(lead.city or lead.preferred_location)
    tehsil_value = _normalize_text(lead.tehsil)
    village_value = _normalize_text(lead.village)

    routing_steps = [
        ("pin_code", pincode_value, agents_for_pincode),
        ("village", village_value, agents_for_village),
        ("tehsil", tehsil_value, agents_for_tehsil),
        ("district", district_value, agents_for_district),
        ("state", state_value, agents_for_state),
        ("city", city_value, agents_for_city),
    ]

    for match_level, raw_value, matcher in routing_steps:
        if not raw_value:
            continue
        candidates = [agent for agent in matcher(raw_value, company=company) if agent.id not in exclude_agent_ids]
        chosen = _best_candidate(candidates, lead)
        if chosen:
            return assign_lead(
                lead,
                agent=chosen,
                reason=f"Auto-assigned using {match_level.replace('_', ' ')} match: {raw_value}",
                match_level=match_level,
                assignment_type=LeadAssignmentLog.AssignmentType.AUTO,
            )

    nearest = [
        agent
        for agent in nearest_agents(
            _coerce_float(lead.latitude or lead.geo_location.get("lat") or lead.geo_location.get("latitude")),
            _coerce_float(lead.longitude or lead.geo_location.get("lng") or lead.geo_location.get("longitude")),
            company=company,
        )
        if agent.id not in exclude_agent_ids
    ]
    chosen = _best_candidate(nearest, lead)
    if chosen:
        return assign_lead(
            lead,
            agent=chosen,
            reason="Auto-assigned to nearest available agent.",
            match_level="nearest",
            assignment_type=LeadAssignmentLog.AssignmentType.AUTO,
        )

    if fallback_agent and fallback_agent.id not in exclude_agent_ids:
        return assign_lead(
            lead,
            agent=fallback_agent,
            reason="Assigned using fallback agent.",
            match_level="fallback",
            assignment_type=LeadAssignmentLog.AssignmentType.AUTO,
        )

    pool = Agent.objects.filter(
        is_active=True,
        is_blocked=False,
        approval_status=Agent.ApprovalStatus.APPROVED,
    ).exclude(id__in=exclude_agent_ids)
    if company:
        pool = pool.filter(Q(user__company=company) | Q(user__company__isnull=True))
    chosen = pick_agent_round_robin(pool, company=company)
    if chosen:
        return assign_lead(
            lead,
            agent=chosen,
            reason="Auto-assigned using round-robin fallback.",
            match_level="fallback",
            assignment_type=LeadAssignmentLog.AssignmentType.AUTO,
        )

    if fallback_user:
        lead.assigned_to = fallback_user
        lead.distribution_level = "fallback"
        lead.distribution_reason = "Assigned to fallback user."
        lead.assigned_at = timezone.now()
        lead.save(update_fields=["assigned_to", "distribution_level", "distribution_reason", "assigned_at", "updated_at"])
    return lead


def compute_lead_score(lead: Lead) -> tuple[int, str]:
    score = 10

    if lead.budget:
        budget = Decimal(str(lead.budget))
        if budget >= Decimal("10000000"):
            score += 25
        elif budget >= Decimal("5000000"):
            score += 20
        elif budget >= Decimal("1000000"):
            score += 15
        else:
            score += 8

    if lead.last_contacted_at:
        delta = lead.last_contacted_at - lead.created_at
        minutes = delta.total_seconds() / 60
        if minutes <= 30:
            score += 15
        elif minutes <= 180:
            score += 10
        elif minutes <= 1440:
            score += 5
    else:
        score -= 5

    recent_activities = lead.activities.filter(created_at__gte=timezone.now() - timedelta(days=7)).count()
    score += min(recent_activities * 2, 15)

    if lead.assignments.filter(is_active=True, first_contact_at__isnull=False).exists():
        score += 8
    if lead.is_duplicate:
        score -= 10
    if lead.interest_type == Lead.InterestType.BUY:
        score += 5

    has_visit = SiteVisit.objects.filter(lead=lead, status=SiteVisit.Status.SCHEDULED).exists()
    completed_visit = SiteVisit.objects.filter(lead=lead, status=SiteVisit.Status.COMPLETED).exists()
    if completed_visit:
        score += 15
    elif has_visit:
        score += 8

    if lead.preferred_location:
        score += 5
    if lead.status == Lead.Status.CONVERTED:
        score = max(score, 90)
    if lead.status == Lead.Status.CLOSED:
        score = 100

    score = max(0, min(100, score))
    if score >= 75:
        temperature = Lead.Temperature.HOT
    elif score >= 50:
        temperature = Lead.Temperature.WARM
    else:
        temperature = Lead.Temperature.COLD
    return score, temperature


def recommend_best_agent(lead: Lead) -> Agent | None:
    candidates = []
    for matcher, value in (
        (agents_for_pincode, lead.pincode_text),
        (agents_for_village, lead.village),
        (agents_for_tehsil, lead.tehsil),
        (agents_for_district, lead.district),
        (agents_for_state, lead.state),
        (agents_for_city, lead.city or lead.preferred_location),
    ):
        if value:
            candidates = list(matcher(value, company=lead.company))
            if candidates:
                break
    if not candidates:
        candidates = list(
            Agent.objects.filter(
                is_active=True,
                is_blocked=False,
                approval_status=Agent.ApprovalStatus.APPROVED,
            ).filter(Q(user__company=lead.company) | Q(user__company__isnull=True))
        )
    return _best_candidate(candidates, lead)


def match_properties_for_lead(lead: Lead, limit: int = 5):
    from leads.models import Property

    qs = Property.objects.exclude(status__in=[Property.Status.REJECTED, Property.Status.DRAFT])

    lead_pin_code = (
        getattr(getattr(lead, "pincode", None), "code", None)
        or getattr(getattr(lead, "pin_code", None), "code", None)
        or getattr(lead, "pin_code", "")
        or lead.pincode_text
        or ""
    )
    if lead_pin_code:
        qs = qs.filter(pin_code=lead_pin_code)
    elif lead.village:
        qs = qs.filter(village__iexact=lead.village)
    elif lead.tehsil:
        qs = qs.filter(tehsil__iexact=lead.tehsil)
    elif lead.city or lead.preferred_location:
        qs = qs.filter(city__iexact=(lead.city or lead.preferred_location))
    elif lead.district:
        qs = qs.filter(district__iexact=lead.district)
    elif lead.state:
        qs = qs.filter(state__iexact=lead.state)

    if lead.preferred_property_type:
        qs = qs.filter(property_type=lead.preferred_property_type)
    if lead.preferred_bedrooms:
        qs = qs.filter(bedrooms=lead.preferred_bedrooms)

    if lead.budget:
        budget = Decimal(str(lead.budget))
        low = budget * Decimal("0.8")
        high = budget * Decimal("1.2")
        qs = qs.filter(price__gte=low, price__lte=high)

    return qs.order_by("price")[:limit]


def schedule_followup(lead: Lead, when=None, message=None, *, channel: str = FollowUp.Channel.WHATSAPP):
    when = when or (timezone.now() + timedelta(hours=24))
    msg = message or f"Hi {lead.name or 'there'}, we found properties in your budget. Shall we schedule a visit?"
    followup = FollowUp.objects.create(lead=lead, followup_date=when, message=msg, channel=channel)
    lead.next_followup_at = when
    lead.followup_channel = channel
    lead.save(update_fields=["next_followup_at", "followup_channel", "updated_at"])
    return followup


def process_due_followups(send_func=None):
    now = timezone.now()
    due = FollowUp.objects.filter(status=FollowUp.Status.PENDING, followup_date__lte=now)
    for followup in due:
        try:
            _send_followup(followup, send_func)
            followup.status = FollowUp.Status.SENT
            followup.processed_at = now
            followup.attempts = (followup.attempts or 0) + 1
            followup.last_error = ""
            followup.lead.last_followup_at = now
            followup.lead.save(update_fields=["last_followup_at", "updated_at"])
        except Exception as exc:
            followup.status = FollowUp.Status.FAILED
            followup.attempts = (followup.attempts or 0) + 1
            followup.last_error = str(exc)[:255]
        followup.save(update_fields=["status", "attempts", "processed_at", "last_error"])


def send_inactive_lead_followups(*, inactivity_hours: int = 24) -> int:
    cutoff = timezone.now() - timedelta(hours=inactivity_hours)
    leads = (
        Lead.objects.exclude(status__in=[Lead.Status.CLOSED, Lead.Status.LOST, Lead.Status.CONVERTED])
        .filter(Q(last_contacted_at__lt=cutoff) | Q(last_contacted_at__isnull=True, created_at__lt=cutoff))
        .order_by("created_at")
    )
    created = 0
    for lead in leads:
        if lead.followups.filter(created_at__gte=timezone.now() - timedelta(hours=inactivity_hours)).exists():
            continue
        schedule_followup(lead, channel=FollowUp.Channel.WHATSAPP)
        created += 1
    return created


def refresh_lead_score(lead: Lead) -> Lead:
    score, temp = compute_lead_score(lead)
    lead.score = score
    lead.lead_score = score
    lead.temperature = temp
    if lead.assigned_agent_id:
        _refresh_agent_metrics(lead.assigned_agent)
    lead.save(update_fields=["score", "lead_score", "temperature", "updated_at"])
    return lead


def send_whatsapp_or_notify(to_number: str, message: str, fallback_user=None):
    try:
        from whatsapp.api_connector import send_whatsapp_message

        response = send_whatsapp_message(to=to_number, message=message)
        if getattr(response, "ok", False):
            return True
    except Exception:
        pass
    if fallback_user:
        notify_user(user=fallback_user, title="WhatsApp message", body=message, level="info")
    return False


def send_lead_message(
    lead: Lead,
    *,
    channel: str,
    message: str = "",
    subject: str = "",
    actor=None,
    phone: str = "",
    email: str = "",
    metadata=None,
):
    metadata = metadata or {}
    channel = _normalize_text(channel).lower()
    phone = _normalize_phone(phone or lead.mobile or getattr(getattr(lead, "assigned_agent", None), "phone", ""))
    email = _normalize_email(email or lead.email)

    if channel == "email":
        email_log = log_email(
            recipient=email or _normalize_email(getattr(getattr(lead, "assigned_to", None), "email", "")),
            subject=subject or f"Lead update for {lead.name or lead.mobile}",
            body=message,
            sender=getattr(actor, "email", ""),
            company=lead.company,
            metadata={"lead_id": lead.id, **metadata},
        )
        LeadActivity.objects.create(lead=lead, actor=actor, activity_type="email", note=message[:300], payload={"email_log_id": email_log.id})
        lead.touch_contacted()
        mark_assignment_responded(lead, actor=actor)
        return {"email_log_id": email_log.id, "channel": channel}

    if channel == "sms":
        sms_log = log_sms(phone=phone, message=message, company=lead.company, metadata={"lead_id": lead.id, **metadata})
        LeadActivity.objects.create(lead=lead, actor=actor, activity_type="sms", note=message[:300], payload={"sms_log_id": sms_log.id})
        lead.touch_contacted()
        mark_assignment_responded(lead, actor=actor)
        return {"sms_log_id": sms_log.id, "channel": channel}

    if channel in {"whatsapp", "messenger", "instagram_dm"}:
        provider = {
            "whatsapp": "whatsapp",
            "messenger": "facebook_messenger",
            "instagram_dm": "instagram_dm",
        }[channel]
        message_log = log_message(
            sender=actor,
            receiver=lead.assigned_to,
            lead=lead,
            message_type=MessageLog.MessageType.WHATSAPP if channel == "whatsapp" else MessageLog.MessageType.CHAT,
            message=message,
            metadata={"lead_id": lead.id, **metadata},
            provider=provider,
        )
        LeadActivity.objects.create(lead=lead, actor=actor, activity_type=channel, note=message[:300], payload={"message_log_id": message_log.id})
        lead.touch_contacted()
        mark_assignment_responded(lead, actor=actor)
        return {"message_log_id": message_log.id, "channel": channel}

    LeadActivity.objects.create(lead=lead, actor=actor, activity_type="call", note=message[:300] or "Call initiated", payload=metadata)
    lead.touch_contacted()
    mark_assignment_responded(lead, actor=actor)
    return {"channel": "call"}


def build_lead_timeline(lead: Lead, *, limit: int = 50) -> list[dict]:
    rows: list[dict] = []
    for activity in lead.activities.order_by("-created_at")[:limit]:
        rows.append(
            {
                "id": f"activity-{activity.id}",
                "kind": "activity",
                "timestamp": activity.created_at,
                "title": activity.activity_type.replace("_", " ").title(),
                "body": activity.note,
                "payload": activity.payload,
            }
        )
    for assignment in lead.assignments.order_by("-created_at")[:limit]:
        rows.append(
            {
                "id": f"assignment-{assignment.id}",
                "kind": "assignment",
                "timestamp": assignment.created_at,
                "title": f"Assigned to {assignment.agent.name}",
                "body": assignment.reason or assignment.matched_on,
                "payload": {"matched_on": assignment.matched_on, "is_active": assignment.is_active},
            }
        )
    for message in lead.message_logs.order_by("-created_at")[:limit]:
        rows.append(
            {
                "id": f"message-{message.id}",
                "kind": "message",
                "timestamp": message.created_at,
                "title": message.provider or message.message_type,
                "body": message.message,
                "payload": message.metadata,
            }
        )
    rows.sort(key=lambda item: item["timestamp"], reverse=True)
    return rows[:limit]


def build_monitoring_snapshot(queryset):
    from crm.models import CallLog

    lead_ids = list(queryset.values_list("id", flat=True))
    closed_qs = queryset.filter(status__in=[Lead.Status.CONVERTED, Lead.Status.CLOSED])
    total_revenue = sum(Decimal(str(value or 0)) for value in closed_qs.values_list("deal_value", flat=True))
    active_conversations = (
        MessageLog.objects.filter(lead_id__in=lead_ids).count()
        + EmailLog.objects.filter(metadata__lead_id__in=lead_ids).count()
        + SMSLog.objects.filter(metadata__lead_id__in=lead_ids).count()
        + CallLog.objects.filter(lead_id__in=lead_ids).count()
    )
    return {
        "total_leads": queryset.count(),
        "new_today": queryset.filter(created_at__date=timezone.localdate()).count(),
        "conversion_rate": round((closed_qs.count() / queryset.count()) * 100, 2) if queryset.exists() else 0,
        "status_breakdown": list(queryset.values("status").annotate(count=Count("id")).order_by()),
        "source_breakdown": list(queryset.values("source").annotate(count=Count("id")).order_by()),
        "assigned": queryset.filter(assigned_agent__isnull=False).count(),
        "duplicates": queryset.filter(is_duplicate=True).count(),
        "converted": queryset.filter(status=Lead.Status.CONVERTED).count(),
        "active_conversations": active_conversations,
        "total_revenue": total_revenue,
        "agent_performance": list(
            closed_qs.values("assigned_agent", "assigned_agent__name").annotate(closed=Count("id"))
        ),
    }


IMPORT_FIELD_ALIASES = {
    "name": ("name", "full_name", "fullname", "lead_name", "customer_name", "contact_name"),
    "phone": ("phone", "mobile", "mobile_number", "contact", "contact_no", "whatsapp_number"),
    "email": ("email", "mail", "email_address"),
    "source": ("source", "lead_source", "channel", "source_name"),
    "city": ("city", "town"),
    "district": ("district",),
    "state": ("state",),
    "tehsil": ("tehsil",),
    "village": ("village",),
    "pincode": ("pincode", "pin_code", "postcode", "zip"),
    "budget": ("budget", "deal_value", "value", "price"),
    "notes": ("notes", "note", "comment", "remarks"),
}

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:(?:\+?\d[\d\s().-]{7,}\d))")


def _read_upload_bytes(upload) -> bytes:
    if upload is None:
        return b""
    try:
        upload.seek(0)
    except Exception:
        pass
    if hasattr(upload, "read"):
        data = upload.read()
    else:
        data = bytes(upload)
    try:
        upload.seek(0)
    except Exception:
        pass
    return data or b""


def _normalize_mapping(mapping) -> dict:
    if not mapping or not isinstance(mapping, dict):
        return {}
    normalized = {}
    for key, value in mapping.items():
        key = _normalize_text(key).lower()
        if not key:
            continue
        if isinstance(value, (list, tuple, set)):
            normalized[key] = [str(item) for item in value if _normalize_text(item)]
        else:
            value = _normalize_text(value)
            normalized[key] = [value] if value else []
    return normalized


def _coerce_row_value(row: dict, alias) -> str:
    aliases = alias if isinstance(alias, (list, tuple, set)) else (alias,)
    lower_row = {str(key).strip().lower(): value for key, value in (row or {}).items()}
    for candidate in aliases:
        candidate = _normalize_text(candidate).lower()
        if candidate in lower_row:
            value = lower_row[candidate]
            if value is not None:
                return str(value).strip()
    return ""


def _apply_mapping_to_row(row: dict, mapping: dict | None = None) -> dict:
    mapping = _normalize_mapping(mapping)
    source_row = {str(key).strip().lower(): ("" if value is None else str(value).strip()) for key, value in (row or {}).items()}

    def _value(field: str) -> str:
        if field in mapping and mapping[field]:
            return _coerce_row_value(source_row, mapping[field])
        return _coerce_row_value(source_row, IMPORT_FIELD_ALIASES[field])

    result = {
        "name": _value("name"),
        "phone": _value("phone"),
        "email": _value("email"),
        "source": _value("source") or Lead.Source.MANUAL,
        "city": _value("city"),
        "district": _value("district"),
        "state": _value("state"),
        "tehsil": _value("tehsil"),
        "village": _value("village"),
        "pincode": _value("pincode"),
        "budget": _value("budget"),
        "notes": _value("notes"),
        "metadata": {"raw_row": row},
    }
    if not result["source"]:
        result["source"] = Lead.Source.MANUAL
    return result


def _validate_import_row(row: dict) -> list[str]:
    errors = []
    phone = _normalize_phone(row.get("phone"))
    email = _normalize_email(row.get("email"))
    if not phone and not email:
        errors.append("Phone or email is required.")
    if phone and len(phone) < 10:
        errors.append("Phone number looks invalid.")
    if email and "@" not in email:
        errors.append("Email looks invalid.")
    return errors


def _has_merge_value(value) -> bool:
    return value not in (None, "", 0, 0.0, {}, [])


def _column_index_from_ref(cell_ref: str) -> int:
    letters = "".join(ch for ch in str(cell_ref or "") if ch.isalpha()).upper()
    index = 0
    for char in letters:
        index = index * 26 + (ord(char) - 64)
    return max(0, index - 1)


def _parse_csv_rows(raw_bytes: bytes) -> tuple[list[str], list[dict]]:
    text = raw_bytes.decode("utf-8-sig", errors="ignore")
    reader = csv.DictReader(io.StringIO(text))
    headers = list(reader.fieldnames or [])
    rows = [{key: value for key, value in (row or {}).items()} for row in reader]
    return headers, rows


def _parse_xlsx_rows(raw_bytes: bytes) -> tuple[list[str], list[dict]]:
    with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
        shared_strings = []
        try:
            shared_root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            for shared in shared_root.findall(".//a:si", ns):
                parts = []
                for node in shared.iter():
                    if node.tag.endswith("}t") and node.text:
                        parts.append(node.text)
                shared_strings.append("".join(parts))
        except Exception:
            shared_strings = []

        workbook_root = ET.fromstring(zf.read("xl/workbook.xml"))
        workbook_ns = {
            "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
            "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        }
        sheet = workbook_root.find(".//a:sheets/a:sheet", workbook_ns)
        rel_id = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id") if sheet is not None else ""

        rels_root = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        rel_target = "worksheets/sheet1.xml"
        for rel in rels_root:
            if rel.attrib.get("Id") == rel_id:
                rel_target = rel.attrib.get("Target") or rel_target
                break
        sheet_path = rel_target if rel_target.startswith("xl/") else f"xl/{rel_target.lstrip('/')}"

        sheet_root = ET.fromstring(zf.read(sheet_path))
        ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        matrix = []
        for row in sheet_root.findall(".//a:sheetData/a:row", ns):
            values = []
            for cell in row.findall("a:c", ns):
                index = _column_index_from_ref(cell.attrib.get("r", ""))
                while len(values) <= index:
                    values.append("")
                cell_type = cell.attrib.get("t", "")
                raw_value = ""
                value_node = cell.find("a:v", ns)
                if value_node is not None and value_node.text is not None:
                    raw_value = value_node.text
                if cell_type == "s":
                    try:
                        raw_value = shared_strings[int(raw_value)]
                    except Exception:
                        pass
                elif cell_type == "inlineStr":
                    text_parts = []
                    for node in cell.iter():
                        if node.tag.endswith("}t") and node.text:
                            text_parts.append(node.text)
                    raw_value = "".join(text_parts)
                values[index] = html.unescape(str(raw_value).strip())
            matrix.append(values)

    if not matrix:
        return [], []
    headers = [str(item).strip() for item in matrix[0]]
    rows = []
    for row_values in matrix[1:]:
        row = {}
        for index, header in enumerate(headers):
            key = header or f"column_{index + 1}"
            row[key] = row_values[index] if index < len(row_values) else ""
        rows.append(row)
    return headers, rows


def parse_lead_import_file(upload, *, mapping=None, preview_limit: int = 25):
    raw_bytes = _read_upload_bytes(upload)
    filename = (getattr(upload, "name", "") or "").lower()
    if filename.endswith(".xlsx"):
        file_type = "xlsx"
        headers, rows = _parse_xlsx_rows(raw_bytes)
    else:
        file_type = "csv"
        headers, rows = _parse_csv_rows(raw_bytes)

    mapping = _normalize_mapping(mapping)
    mapped_rows = [_apply_mapping_to_row(row, mapping) for row in rows]
    preview_rows = []
    issues = []
    for index, row in enumerate(mapped_rows[:preview_limit], start=1):
        row_issues = _validate_import_row(row)
        if row_issues:
            issues.append({"row": index, "errors": row_issues, "data": row})
        preview_rows.append(
            {
                "row_number": index,
                "name": row.get("name", ""),
                "phone": row.get("phone", ""),
                "email": row.get("email", ""),
                "source": row.get("source", ""),
                "city": row.get("city", ""),
                "district": row.get("district", ""),
                "state": row.get("state", ""),
                "pincode": row.get("pincode", ""),
                "budget": row.get("budget", ""),
                "notes": row.get("notes", ""),
                "errors": row_issues,
                "raw": row.get("metadata", {}).get("raw_row", {}),
            }
        )
    return {
        "file_type": file_type,
        "headers": headers,
        "rows": mapped_rows,
        "preview_rows": preview_rows,
        "issues": issues,
        "total_rows": len(mapped_rows),
    }


def _extract_candidate_name(html_text: str, fallback: str = "") -> str:
    candidates = []
    patterns = [
        r"<title[^>]*>(.*?)</title>",
        r"<h1[^>]*>(.*?)</h1>",
        r"<h2[^>]*>(.*?)</h2>",
        r"<h3[^>]*>(.*?)</h3>",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, html_text, flags=re.IGNORECASE | re.DOTALL):
            text = re.sub(r"<[^>]+>", " ", match)
            text = re.sub(r"\s+", " ", text).strip()
            if text:
                candidates.append(html.unescape(text))
    if candidates:
        return candidates[0][:160]
    return fallback[:160]


def _scrape_candidate_rows(*, url: str, html_text: str, max_items: int = 25) -> list[dict]:
    source_name = _extract_candidate_name(html_text, fallback=url)
    tel_numbers = []
    mail_addresses = []
    for href in re.findall(r'href=["\']([^"\']+)["\']', html_text, flags=re.IGNORECASE):
        if href.lower().startswith("mailto:"):
            mail_addresses.append(href.split(":", 1)[1].split("?", 1)[0])
        elif href.lower().startswith("tel:"):
            tel_numbers.append(_normalize_phone(href.split(":", 1)[1]))
    mail_addresses.extend(EMAIL_RE.findall(html_text))
    tel_numbers.extend(_normalize_phone(match) for match in PHONE_RE.findall(html_text))
    mail_addresses = [email for email in dict.fromkeys(_normalize_email(email) for email in mail_addresses) if email]
    tel_numbers = [phone for phone in dict.fromkeys(tel_numbers) if phone]

    candidate_count = min(max_items, max(len(mail_addresses), len(tel_numbers), 1))
    rows = []
    for index in range(candidate_count):
        rows.append(
            {
                "name": f"{source_name} Lead {index + 1}" if candidate_count > 1 else source_name,
                "phone": tel_numbers[index] if index < len(tel_numbers) else "",
                "email": mail_addresses[index] if index < len(mail_addresses) else "",
                "source": Lead.Source.WEBSITE,
                "notes": f"Scraped from {url}",
                "metadata": {
                    "source_url": url,
                    "scraped_source": source_name,
                    "scrape_index": index + 1,
                    "ingest_channel": "web_scrape",
                },
            }
        )
    return rows


def scrape_leads_from_page(
    *,
    url: str,
    company=None,
    actor=None,
    source_config: LeadSource | None = None,
    auto_assign: bool = True,
    max_items: int = 25,
    raw_html: str = "",
):
    html_text = raw_html.strip()
    if not html_text:
        response = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0 LeadBot/1.0"})
        response.raise_for_status()
        html_text = response.text
    rows = _scrape_candidate_rows(url=url, html_text=html_text, max_items=max_items)
    if not rows:
        raise ValueError("No lead data found on the provided page.")
    batch = import_leads_from_rows(
        rows,
        company=company,
        actor=actor,
        source_config=source_config,
        import_type=LeadImportBatch.ImportType.WEB_SCRAPE,
        source_name=url,
        auto_assign=auto_assign,
    )
    return batch, rows


@transaction.atomic
def merge_duplicate_leads(*, primary: Lead, duplicate: Lead, actor=None, note: str = ""):
    if primary.id == duplicate.id:
        return primary

    fields_to_fill = [
        "company",
        "source_config",
        "created_by",
        "assigned_to",
        "assigned_agent",
        "interested_property",
        "converted_customer",
        "name",
        "mobile",
        "email",
        "deal_value",
        "stage",
        "interest_type",
        "property_type",
        "budget",
        "preferred_location",
        "geo_location",
        "lead_score",
        "customer_type",
        "reliability_score",
        "no_show_count",
        "temperature",
        "preferred_property_type",
        "preferred_bedrooms",
        "latitude",
        "longitude",
        "country",
        "state",
        "district",
        "tehsil",
        "village",
        "city",
        "notes",
        "source",
        "status",
        "pincode_text",
        "pincode",
        "metadata",
        "distribution_level",
        "distribution_reason",
        "next_followup_at",
        "last_followup_at",
        "followup_channel",
        "last_contacted_at",
        "stage_updated_at",
        "stage_deadline",
        "is_overdue",
    ]
    update_fields = []
    for field_name in fields_to_fill:
        primary_value = getattr(primary, field_name, None)
        duplicate_value = getattr(duplicate, field_name, None)
        if not _has_merge_value(primary_value) and _has_merge_value(duplicate_value):
            setattr(primary, field_name, duplicate_value)
            update_fields.append(field_name)

    if duplicate.assigned_agent_id and not primary.assigned_agent_id:
        primary.assigned_agent = duplicate.assigned_agent
        update_fields.append("assigned_agent")
    if duplicate.assigned_to_id and not primary.assigned_to_id:
        primary.assigned_to = duplicate.assigned_to
        update_fields.append("assigned_to")

    merged_metadata = dict(primary.metadata or {})
    merged_metadata.setdefault("merged_duplicate_ids", [])
    merged_metadata["merged_duplicate_ids"] = sorted(
        set([*(merged_metadata.get("merged_duplicate_ids") or []), duplicate.id])
    )
    merged_metadata["merged_from_duplicate_id"] = duplicate.id
    primary.metadata = merged_metadata
    update_fields.append("metadata")

    primary.save(update_fields=list(dict.fromkeys([*update_fields, "updated_at"])))

    LeadActivity.objects.create(
        lead=primary,
        actor=actor,
        activity_type="merge",
        note=(note or f"Merged duplicate lead #{duplicate.id}")[:500],
        payload={"duplicate_id": duplicate.id, "primary_id": primary.id},
    )

    for model in (LeadActivity, LeadAssignmentLog, LeadAssignment, FollowUp):
        try:
            model.objects.filter(lead=duplicate).update(lead=primary)
        except Exception:
            continue
    try:
        from leads.models import LeadDocument

        LeadDocument.objects.filter(lead=duplicate).update(lead=primary)
    except Exception:
        pass

    duplicate.is_duplicate = True
    duplicate.duplicate_of = primary
    duplicate.duplicate_reason = (note or f"Merged into lead #{primary.id}")[:160]
    duplicate.save(update_fields=["is_duplicate", "duplicate_of", "duplicate_reason", "updated_at"])
    refresh_lead_score(primary)
    return primary


def bulk_assign_leads(*, leads: Sequence[Lead], agent: Agent | None = None, actor=None, reason: str = "", auto: bool = False):
    updated = []
    for lead in leads:
        if auto:
            lead.assigned_agent = None
            lead.assigned_to = None
            lead.save(update_fields=["assigned_agent", "assigned_to", "updated_at"])
            updated.append(auto_assign_lead(lead=lead))
        elif agent:
            updated.append(
                assign_lead(
                    lead,
                    agent=agent,
                    actor=actor,
                    reason=reason or "Bulk assignment",
                    match_level="manual",
                    assignment_type=LeadAssignmentLog.AssignmentType.MANUAL,
                )
            )
    return updated


def import_leads_from_rows(
    rows: Sequence[dict],
    *,
    company=None,
    actor=None,
    source_config: LeadSource | None = None,
    import_type: str = LeadImportBatch.ImportType.MANUAL,
    source_name: str = "",
    auto_assign: bool = True,
    batch: LeadImportBatch | None = None,
) -> LeadImportBatch:
    batch = batch or LeadImportBatch.objects.create(
        company=company,
        source=source_config,
        created_by=actor,
        import_type=import_type,
        status=LeadImportBatch.Status.PROCESSING,
        total_rows=len(rows),
        source_name=source_name or getattr(source_config, "name", ""),
    )
    errors = []
    created_count = 0
    duplicate_count = 0
    failed_count = 0

    for index, row in enumerate(rows, start=1):
        try:
            lead, _ = ingest_lead_payload(
                row,
                company=company,
                actor=actor,
                source_config=source_config,
                import_batch=batch,
                auto_assign=auto_assign,
            )
            created_count += 1
            if lead.is_duplicate:
                duplicate_count += 1
        except Exception as exc:
            failed_count += 1
            errors.append({"row": index, "error": str(exc)[:300], "payload": row})

    batch.processed_rows = len(rows)
    batch.created_leads = created_count
    batch.duplicate_rows = duplicate_count
    batch.failed_rows = failed_count
    batch.error_report = errors[:100]
    batch.status = LeadImportBatch.Status.FAILED if failed_count and not created_count else LeadImportBatch.Status.COMPLETED
    batch.save(
        update_fields=[
            "processed_rows",
            "created_leads",
            "duplicate_rows",
            "failed_rows",
            "error_report",
            "status",
            "updated_at",
        ]
    )
    return batch


def ingest_lead_payload(
    payload: dict,
    *,
    company=None,
    actor=None,
    source_config: LeadSource | None = None,
    import_batch: LeadImportBatch | None = None,
    auto_assign: bool = True,
) -> tuple[Lead, bool]:
    phone = _normalize_phone(payload.get("phone") or payload.get("mobile"))
    email = _normalize_email(payload.get("email"))
    if not phone and not email:
        raise ValueError("Lead payload requires phone or email.")

    duplicate = find_duplicate_lead(company=company, phone=phone, email=email)
    source_value = _normalize_text(payload.get("source")) or getattr(source_config, "source_value", "") or Lead.Source.API
    pincode_value = _normalize_text(payload.get("pincode") or payload.get("pincode_text") or payload.get("pin_code"))
    pincode_obj = None
    if pincode_value:
        try:
            from location.models import Pincode

            pincode_obj = Pincode.objects.filter(code=pincode_value).first()
        except Exception:
            pincode_obj = None

    metadata = payload.get("metadata") or {}
    if import_batch:
        metadata = {**metadata, "import_batch_id": import_batch.id}

    lead = Lead.objects.create(
        company=company,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
        source_config=source_config,
        duplicate_of=duplicate,
        is_duplicate=bool(duplicate),
        duplicate_reason="Matched by phone/email" if duplicate else "",
        name=_normalize_text(payload.get("name")),
        mobile=phone,
        email=email,
        source=source_value,
        status=payload.get("status") or Lead.Status.NEW,
        stage=payload.get("stage") or Lead.Stage.NEW,
        interest_type=payload.get("interest_type") or Lead.InterestType.BUY,
        deal_value=payload.get("deal_value") or 0,
        property_type=_normalize_text(payload.get("property_type")),
        budget=payload.get("budget") or None,
        preferred_location=_normalize_text(payload.get("preferred_location") or payload.get("city")),
        geo_location=payload.get("geo_location") or {},
        preferred_property_type=_normalize_text(payload.get("preferred_property_type")),
        preferred_bedrooms=payload.get("preferred_bedrooms") or None,
        latitude=payload.get("latitude") or None,
        longitude=payload.get("longitude") or None,
        country=_normalize_text(payload.get("country")),
        state=_normalize_text(payload.get("state")),
        district=_normalize_text(payload.get("district")),
        tehsil=_normalize_text(payload.get("tehsil")),
        village=_normalize_text(payload.get("village")),
        city=_normalize_text(payload.get("city")),
        pincode_text=pincode_value,
        pincode=pincode_obj,
        notes=_normalize_text(payload.get("notes")),
        metadata=metadata,
    )

    refresh_lead_score(lead)
    if auto_assign and (not source_config or source_config.auto_assign):
        auto_assign_lead(lead=lead)
    return lead, True


def ensure_customer_from_lead(
    lead: Lead,
    *,
    actor=None,
    customer_name: str = "",
    customer_email: str = "",
    customer_phone: str = "",
):
    UserModel = get_user_model()
    email = _normalize_email(customer_email or lead.email or f"customer-lead-{lead.id}@example.invalid")
    phone = _normalize_phone(customer_phone or lead.mobile or f"900000{lead.id:04d}")
    name = _normalize_text(customer_name or lead.name or f"Customer {lead.id}")
    user = UserModel.objects.filter(Q(email=email) | Q(mobile=phone)).order_by("id").first()
    if not user:
        username_seed = slugify(name) or f"customer-{lead.id}"
        username = username_seed[:120] or f"customer-{lead.id}"
        user = UserModel.objects.create(
            email=email,
            username=username,
            mobile=phone,
            role=SaaSRole.CUSTOMER,
            company=lead.company,
            first_name=name.split(" ")[0][:150],
        )
        user.set_unusable_password()
        user.save(update_fields=["password"])
    else:
        changed = []
        if not getattr(user, "company", None) and lead.company_id:
            user.company = lead.company
            changed.append("company")
        if not getattr(user, "mobile", None) and phone:
            user.mobile = phone
            changed.append("mobile")
        if not getattr(user, "role", ""):
            user.role = SaaSRole.CUSTOMER
            changed.append("role")
        if changed:
            user.save(update_fields=changed)

    from customers.models import Customer

    customer, _ = Customer.objects.get_or_create(
        user=user,
        defaults={
            "company": lead.company,
            "assigned_agent": lead.assigned_agent,
            "preferred_location": lead.preferred_location or lead.city,
            "preferred_budget": lead.budget,
            "property_type": lead.preferred_property_type or lead.property_type,
            "city": lead.city,
            "district": lead.district,
            "state": lead.state,
            "pin_code": lead.pincode_text,
        },
    )
    updates = []
    if lead.company_id and customer.company_id != lead.company_id:
        customer.company = lead.company
        updates.append("company")
    if lead.assigned_agent_id and customer.assigned_agent_id != lead.assigned_agent_id:
        customer.assigned_agent = lead.assigned_agent
        updates.append("assigned_agent")
    if lead.city and not customer.city:
        customer.city = lead.city
        updates.append("city")
    if lead.district and not customer.district:
        customer.district = lead.district
        updates.append("district")
    if lead.state and not customer.state:
        customer.state = lead.state
        updates.append("state")
    if lead.pincode_text and not customer.pin_code:
        customer.pin_code = lead.pincode_text
        updates.append("pin_code")
    if lead.preferred_location and not customer.preferred_location:
        customer.preferred_location = lead.preferred_location
        updates.append("preferred_location")
    if lead.budget and not customer.preferred_budget:
        customer.preferred_budget = lead.budget
        updates.append("preferred_budget")
    if lead.preferred_property_type and not customer.property_type:
        customer.property_type = lead.preferred_property_type
        updates.append("property_type")
    if updates:
        customer.save(update_fields=[*updates, "updated_at"])
    return customer


@transaction.atomic
def convert_lead(
    lead: Lead,
    *,
    actor=None,
    deal_amount: Decimal | None = None,
    commission_rate: Decimal | None = None,
    company_share_percent: Decimal | None = None,
    agent_share_percent: Decimal | None = None,
    customer_name: str = "",
    customer_email: str = "",
    customer_phone: str = "",
    create_payment: bool = True,
    note: str = "",
):
    if not lead.assigned_agent_id:
        best_agent = recommend_best_agent(lead)
        if best_agent:
            assign_lead(
                lead,
                agent=best_agent,
                actor=actor,
                reason="Assigned during conversion.",
                match_level="manual",
                assignment_type=LeadAssignmentLog.AssignmentType.REASSIGN,
            )

    customer = ensure_customer_from_lead(
        lead,
        actor=actor,
        customer_name=customer_name,
        customer_email=customer_email,
        customer_phone=customer_phone,
    )
    amount = Decimal(str(deal_amount or lead.deal_value or lead.budget or 0))
    if amount <= 0:
        amount = Decimal("0.00")
    rate = Decimal(str(commission_rate or getattr(lead.assigned_agent, "commission_rate", Decimal("2.00")) or "2.00"))
    company_share = Decimal(str(company_share_percent or "50.00"))
    agent_share = Decimal(str(agent_share_percent or "50.00"))
    commission_amount = (amount * rate) / Decimal("100.00") if amount > 0 else Decimal("0.00")

    deal, _ = Deal.objects.update_or_create(
        lead=lead,
        defaults={
            "company": lead.company,
            "customer": customer,
            "property": lead.interested_property,
            "agent": lead.assigned_agent,
            "deal_amount": amount,
            "commission_rate": rate,
            "company_share_percent": company_share,
            "agent_share_percent": agent_share,
            "commission_amount": commission_amount,
            "status": Deal.Status.WON,
            "stage": Deal.Stage.CLOSED,
            "closing_date": timezone.localdate(),
            "closed_at": timezone.now(),
            "metadata": {"conversion_note": note, "converted_by": getattr(actor, "id", None)},
        },
    )
    Commission.objects.update_or_create(
        deal=deal,
        defaults={
            "company": lead.company,
            "total_amount": commission_amount,
            "admin_amount": (commission_amount * company_share) / Decimal("100.00"),
            "agent_amount": (commission_amount * agent_share) / Decimal("100.00"),
            "metadata": {"lead_id": lead.id},
        },
    )

    if create_payment and amount > 0:
        Payment.objects.update_or_create(
            deal=deal,
            payment_type=Payment.PaymentType.CUSTOMER_PAYMENT,
            defaults={
                "company": lead.company,
                "lead": lead,
                "customer": customer,
                "agent": lead.assigned_agent,
                "direction": Payment.Direction.INBOUND,
                "amount": amount,
                "status": Payment.Status.APPROVED,
                "approved_by": actor,
                "approved_at": timezone.now(),
                "paid_at": timezone.now(),
                "reference": f"deal-{deal.id}-customer",
            },
        )
        if commission_amount > 0:
            Payment.objects.update_or_create(
                deal=deal,
                payment_type=Payment.PaymentType.AGENT_PAYOUT,
                defaults={
                    "company": lead.company,
                    "lead": lead,
                    "customer": customer,
                    "agent": lead.assigned_agent,
                    "direction": Payment.Direction.OUTBOUND,
                    "amount": (commission_amount * agent_share) / Decimal("100.00"),
                    "status": Payment.Status.PENDING,
                    "reference": f"deal-{deal.id}-agent-payout",
                },
            )

    lead.converted_customer = customer
    lead.converted_at = timezone.now()
    lead.deal_value = amount
    lead.status = Lead.Status.CONVERTED
    lead.stage = Lead.Stage.CONVERTED
    lead.save(update_fields=["converted_customer", "converted_at", "deal_value", "status", "stage", "updated_at"])
    LeadActivity.objects.create(
        lead=lead,
        actor=actor,
        activity_type="converted",
        note=(note or "Lead converted into customer")[:300],
        payload={"deal_id": deal.id, "customer_id": customer.id},
    )
    refresh_lead_score(lead)
    if lead.assigned_agent_id:
        try:
            lead.assigned_agent.record_closure(amount)
        except Exception:
            pass
        _refresh_agent_metrics(lead.assigned_agent)
        try:
            from crm.performance import sync_agent_score

            sync_agent_score(lead.assigned_agent)
        except Exception:
            pass
        try:
            queue_notification_event(
                users=[lead.assigned_agent.user, customer.user],
                title="Lead converted",
                body=f"{lead.name or lead.mobile} converted into a customer.",
                lead=lead,
                channels=["in_app", "email"],
                email=getattr(lead.assigned_agent.user, "email", ""),
                sender=actor,
                metadata={"deal_id": deal.id, "customer_id": customer.id},
            )
        except Exception:
            pass
    try:
        from billing.invoice_engine import create_invoice_for_lead

        invoice_amount = amount if amount > 0 else (Decimal(str(lead.budget or 0)) if lead.budget else Decimal("0.00"))
        if invoice_amount > 0:
            create_invoice_for_lead(lead, deal=deal, actor=actor, amount=invoice_amount, source_note=note or "Lead conversion")
    except Exception:
        pass
    return {"lead": lead, "customer": customer, "deal": deal}


def reassign_stale_leads(*, hours: int = 2) -> int:
    now = timezone.now()
    stale_assignments = LeadAssignment.objects.filter(
        is_active=True,
        first_contact_at__isnull=True,
        response_due_at__lte=now,
    ).select_related("lead", "agent")
    reassigned = 0
    for assignment in stale_assignments:
        lead = assignment.lead
        lead.assigned_agent = None
        lead.assigned_to = None
        lead.save(update_fields=["assigned_agent", "assigned_to", "updated_at"])
        assignment.is_active = False
        assignment.released_at = now
        assignment.save(update_fields=["is_active", "released_at", "updated_at"])
        reassigned_lead = auto_assign_lead(lead=lead, exclude_agent_ids={assignment.agent_id})
        if reassigned_lead.assigned_agent_id and reassigned_lead.assigned_agent_id != assignment.agent_id:
            LeadActivity.objects.create(
                lead=lead,
                activity_type="reassign",
                note="Lead reassigned due to no agent response",
                payload={"from_agent_id": assignment.agent_id, "to_agent_id": reassigned_lead.assigned_agent_id},
            )
            reassigned += 1
    return reassigned


def _send_followup(followup: FollowUp, send_func=None):
    lead = followup.lead
    user = lead.assigned_to or lead.created_by
    body = followup.message
    if send_func:
        send_func(lead, body)
        return
    if followup.channel == FollowUp.Channel.EMAIL and lead.email:
        log_email(recipient=lead.email, subject="Lead follow-up", body=body, company=lead.company, metadata={"lead_id": lead.id})
    elif followup.channel == FollowUp.Channel.SMS and lead.mobile:
        log_sms(phone=lead.mobile, message=body, company=lead.company, metadata={"lead_id": lead.id})
    elif followup.channel == FollowUp.Channel.WHATSAPP and lead.mobile:
        send_whatsapp_or_notify(lead.mobile, body, fallback_user=user)
    else:
        notify_user(user=user, title="Follow-up sent", body=body, level="info", data={"lead_id": lead.id})


def _refresh_agent_metrics(agent: Agent):
    if not agent:
        return
    open_load = Lead.objects.filter(assigned_agent=agent).exclude(
        status__in=[Lead.Status.CLOSED, Lead.Status.LOST, Lead.Status.CONVERTED]
    ).count()
    closed_count = Lead.objects.filter(assigned_agent=agent, status__in=[Lead.Status.CONVERTED, Lead.Status.CLOSED]).count()
    performance_score = min(100, max(0, closed_count * 12 - open_load * 2 + int(agent.rating or 0)))
    if agent.performance_score != performance_score:
        agent.performance_score = performance_score
        agent.save(update_fields=["performance_score", "updated_at"])
