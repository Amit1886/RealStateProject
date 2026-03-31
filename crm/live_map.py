from datetime import timedelta

from django.utils import timezone

from agents.models import AgentLocationLog, Agent


def live_map_data(minutes: int = 15):
    since = timezone.now() - timedelta(minutes=minutes)
    latest_logs = (
        AgentLocationLog.objects.select_related("agent")
        .filter(timestamp__gte=since)
        .order_by("agent_id", "-timestamp")
        .distinct("agent_id")
    )
    live = []
    for log in latest_logs:
        agent = log.agent
        live.append(
            {
                "agent_id": agent.id,
                "agent_name": agent.name,
                "lat": float(log.latitude),
                "lng": float(log.longitude),
                "timestamp": log.timestamp,
                "risk_score": float(agent.risk_score or 0),
                "risk_level": agent.risk_level,
                "is_blocked": agent.is_blocked,
            }
        )

    trails = list(
        AgentLocationLog.objects.filter(timestamp__gte=since)
        .values("agent_id", "latitude", "longitude", "timestamp")
        .order_by("agent_id", "timestamp")
    )
    return {"live": live, "trails": trails}
