from agents.models import Agent, AgentRiskProfile, AgentLocationLog
from crm.dashboard import admin_super_dashboard


def super_intel_dashboard(filters=None):
    data = admin_super_dashboard(filters or {})
    data["high_risk_agents"] = list(
        AgentRiskProfile.objects.filter(risk_level=AgentRiskProfile.RiskLevel.HIGH)
        .values("agent_id", "agent__name", "risk_score", "last_evaluated")
    )
    data["live_agents"] = list(
        Agent.objects.filter(location_updated_at__isnull=False)
        .values("id", "name", "last_latitude", "last_longitude", "location_updated_at")
    )
    return data
