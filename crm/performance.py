from __future__ import annotations

from datetime import datetime, timedelta

from django.db import models
from django.utils import timezone

from rewards.models import Reward

from leads.pipeline import calculate_closing_ratio as _calculate_closing_ratio
from .models import AgentAchievement, AgentScore


def calculate_closing_ratio(agent):
    return _calculate_closing_ratio(agent)


def _score_window(date_value=None):
    date_value = date_value or timezone.localdate()
    start = timezone.make_aware(datetime.combine(date_value, datetime.min.time()))
    end = timezone.make_aware(datetime.combine(date_value, datetime.max.time()))
    return start, end


def sync_agent_score(agent, *, score_date=None):
    from leads.models import Lead, LeadAssignment

    score_date = score_date or timezone.localdate()
    start, end = _score_window(score_date)
    assigned_qs = LeadAssignment.objects.filter(agent=agent, created_at__range=(start, end))
    lead_qs = Lead.objects.filter(assigned_agent=agent, created_at__range=(start, end))
    closed_qs = Lead.objects.filter(
        assigned_agent=agent,
        status__in=[Lead.Status.CONVERTED, Lead.Status.CLOSED, Lead.Status.WON],
        converted_at__range=(start, end),
    )
    response_seconds = 0
    response_count = 0
    for assignment in assigned_qs.filter(first_contact_at__isnull=False).only("created_at", "first_contact_at"):
        delta = assignment.first_contact_at - assignment.created_at
        response_seconds += max(0, int(delta.total_seconds()))
        response_count += 1
    avg_response = int(response_seconds / response_count) if response_count else 0
    points = (lead_qs.count() * 10) + (closed_qs.count() * 50) - min(50, avg_response // 60)
    score, _ = AgentScore.objects.update_or_create(
        agent=agent,
        score_date=score_date,
        defaults={
            "leads_assigned": lead_qs.count(),
            "leads_closed": closed_qs.count(),
            "response_time_seconds": avg_response,
            "points": points,
            "target_points": 100,
            "metadata": {
                "assigned_count": assigned_qs.count(),
                "closed_count": closed_qs.count(),
                "period": str(score_date),
            },
        },
    )
    _award_achievement(agent, score.points, score.leads_closed, avg_response)
    return score


def _award_achievement(agent, points: int, conversions: int, response_seconds: int):
    achievements = [
        ("top_performer", "Top Performer", "badge", "Reached 100 points", 100),
        ("fast_responder", "Fast Responder", "badge", "Average response under 30 minutes", 50),
        ("closer", "Closer", "badge", "Closed 5 or more leads", 75),
    ]
    for code, title, kind, description, threshold in achievements:
        should_award = False
        if code == "top_performer":
            should_award = points >= threshold
        elif code == "fast_responder":
            should_award = response_seconds > 0 and response_seconds <= 1800
        elif code == "closer":
            should_award = conversions >= 5
        if not should_award:
            continue
        AgentAchievement.objects.get_or_create(
            agent=agent,
            code=code,
            defaults={
                "title": title,
                "kind": kind,
                "description": description,
                "points": threshold,
                "metadata": {"source": "gamification"},
            },
        )
        Reward.objects.get_or_create(
            agent=agent,
            title=title,
            defaults={
                "type": Reward.Type.BONUS,
                "condition": description,
                "achieved": True,
                "achieved_at": timezone.now(),
                "metadata": {"code": code, "points": threshold},
            },
        )


def build_leaderboard(*, days: int = 7, limit: int = 20):
    since = timezone.now() - timedelta(days=max(1, int(days)))
    qs = (
        AgentScore.objects.filter(score_date__gte=since.date())
        .values("agent_id", "agent__name", "agent__user__username")
        .annotate(
            points=models.Sum("points"),
            leads_assigned=models.Sum("leads_assigned"),
            leads_closed=models.Sum("leads_closed"),
            best_response=models.Min("response_time_seconds"),
        )
        .order_by("-points", "best_response")[:limit]
    )
    return list(qs)


def agent_stats(agent, *, days: int = 30):
    since = timezone.now() - timedelta(days=max(1, int(days)))
    qs = AgentScore.objects.filter(agent=agent, score_date__gte=since.date())
    aggregate = qs.aggregate(
        points=models.Sum("points"),
        leads_assigned=models.Sum("leads_assigned"),
        leads_closed=models.Sum("leads_closed"),
        best_response=models.Min("response_time_seconds"),
    )
    return {
        "agent_id": agent.id,
        "points": aggregate.get("points") or 0,
        "leads_assigned": aggregate.get("leads_assigned") or 0,
        "leads_closed": aggregate.get("leads_closed") or 0,
        "best_response": aggregate.get("best_response") or 0,
        "achievements": list(agent.achievements.values("code", "title", "kind", "points", "achieved_at")),
    }
