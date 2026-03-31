from __future__ import annotations

import math
from datetime import datetime, timezone as dt_timezone
from typing import Iterable, Sequence

from django.db import models
from django.db.models import Count
from django.utils import timezone

from leads.models import Lead
from .models import Agent


def _active_approved_agents(*, company=None):
    qs = Agent.objects.filter(
        is_active=True,
        is_blocked=False,
        approval_status=Agent.ApprovalStatus.APPROVED,
    )
    company_label = getattr(getattr(company, "_meta", None), "label_lower", "")
    if company and company_label == "core_settings.companysettings":
        qs = qs.filter(models.Q(company=company) | models.Q(company__isnull=True))
    elif company and company_label == "saas_core.company":
        qs = qs.filter(models.Q(user__company=company) | models.Q(user__company__isnull=True))
    return qs.prefetch_related("service_areas", "coverage_areas")


def agents_for_pincode(pincode_value: str, *, company=None) -> Sequence[Agent]:
    """
    Fetch active agents mapped to a PIN code.
    We do the containment check in Python to stay portable across SQLite/Postgres.
    """
    if not pincode_value:
        return []

    qs = _active_approved_agents(company=company)
    candidates = []
    for agent in qs:
        codes = agent.all_pincodes()
        if pincode_value in codes:
            candidates.append(agent)
    return candidates


def agents_for_district(district_value: str, *, company=None) -> Sequence[Agent]:
    if not district_value:
        return []
    target = district_value.strip().lower()
    candidates = []
    for agent in _active_approved_agents(company=company):
        if (agent.district or "").strip().lower() == target:
            candidates.append(agent)
            continue
        for coverage in agent.coverage_areas.all():
            if (coverage.district or "").strip().lower() == target and coverage.is_active:
                candidates.append(agent)
                break
    return candidates


def agents_for_state(state_value: str, *, company=None) -> Sequence[Agent]:
    if not state_value:
        return []
    target = state_value.strip().lower()
    candidates = []
    for agent in _active_approved_agents(company=company):
        if (agent.state or "").strip().lower() == target:
            candidates.append(agent)
            continue
        for coverage in agent.coverage_areas.all():
            if (coverage.state or "").strip().lower() == target and coverage.is_active:
                candidates.append(agent)
                break
    return candidates


def agents_for_tehsil(tehsil_value: str, *, company=None) -> Sequence[Agent]:
    if not tehsil_value:
        return []
    target = tehsil_value.strip().lower()
    candidates = []
    for agent in _active_approved_agents(company=company):
        if (agent.tehsil or "").strip().lower() == target:
            candidates.append(agent)
            continue
        for coverage in agent.coverage_areas.all():
            if (coverage.tehsil or "").strip().lower() == target and coverage.is_active:
                candidates.append(agent)
                break
    return candidates


def agents_for_village(village_value: str, *, company=None) -> Sequence[Agent]:
    if not village_value:
        return []
    target = village_value.strip().lower()
    candidates = []
    for agent in _active_approved_agents(company=company):
        if (agent.village or "").strip().lower() == target:
            candidates.append(agent)
            continue
        for coverage in agent.coverage_areas.all():
            if (coverage.village or "").strip().lower() == target and coverage.is_active:
                candidates.append(agent)
                break
    return candidates


def agents_for_city(city_value: str, *, company=None) -> Sequence[Agent]:
    if not city_value:
        return []
    target = city_value.strip().lower()
    candidates = []
    for agent in _active_approved_agents(company=company):
        if (agent.city or "").strip().lower() == target:
            candidates.append(agent)
            continue
        for coverage in agent.coverage_areas.all():
            if (coverage.city or "").strip().lower() == target and coverage.is_active:
                candidates.append(agent)
                break
    return candidates


def nearest_agents(latitude: float | None, longitude: float | None, *, company=None, limit: int = 10) -> Sequence[Agent]:
    if latitude is None or longitude is None:
        return []

    def _coord(agent: Agent):
        lat = agent.current_latitude or agent.last_latitude
        lng = agent.current_longitude or agent.last_longitude
        if lat is None or lng is None:
            return None
        return float(lat), float(lng)

    def _distance_km(a_lat: float, a_lng: float, b_lat: float, b_lng: float) -> float:
        radius = 6371.0
        lat1 = math.radians(a_lat)
        lon1 = math.radians(a_lng)
        lat2 = math.radians(b_lat)
        lon2 = math.radians(b_lng)
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        hav = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        return 2 * radius * math.asin(math.sqrt(hav))

    ranked = []
    for agent in _active_approved_agents(company=company):
        coord = _coord(agent)
        if not coord:
            continue
        ranked.append((_distance_km(latitude, longitude, coord[0], coord[1]), agent))
    ranked.sort(key=lambda item: item[0])
    return [agent for _, agent in ranked[:limit]]


def pick_agent_round_robin(candidates: Iterable[Agent], *, company=None) -> Agent | None:
    """
    Pick the agent with the lightest open-lead load; tie-breaker by last assignment timestamp.
    """
    candidates = list(candidates)
    if not candidates:
        return None

    loads = (
        Lead.objects.filter(assigned_agent__in=candidates)
        .exclude(status__in=[Lead.Status.CLOSED, Lead.Status.WON, Lead.Status.LOST])
        .values("assigned_agent")
        .annotate(c=Count("id"))
    )
    load_map = {row["assigned_agent"]: row["c"] for row in loads}

    def _score(agent: Agent):
        return (load_map.get(agent.id, 0), agent.last_assigned_at or datetime(1970, 1, 1, tzinfo=dt_timezone.utc))

    return sorted(candidates, key=_score)[0]
