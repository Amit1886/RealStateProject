from __future__ import annotations

from decimal import Decimal

from agents.models import Agent
from leads.models import Lead


def agent_performance_score(agent: Agent) -> Decimal:
    perf = agent.performance or {}
    closed = Decimal(str(perf.get("closed_leads", 0)))
    revenue = Decimal(str(perf.get("revenue", 0)))
    return closed * Decimal("2.0") + revenue / Decimal("100000")


def agent_workload(agent: Agent) -> int:
    return Lead.objects.filter(assigned_agent=agent).exclude(status=Lead.Status.CLOSED).count()
