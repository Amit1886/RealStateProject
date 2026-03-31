from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from agents.models import Agent, AgentRiskProfile
from agents.wallet import WalletTransaction
from deals.models import Deal
from visits.models import SiteVisit
from leads.models import Lead
from utils.geo import calculate_distance


def calculate_risk(agent: Agent) -> AgentRiskProfile:
    risk = 0
    notes = {}

    # conversion rate too high
    total_leads = Lead.objects.filter(assigned_agent=agent).count()
    closed = Lead.objects.filter(assigned_agent=agent, status=Lead.Status.CLOSED).count()
    conv = (closed / total_leads) * 100 if total_leads else 0
    notes["conversion"] = conv
    if conv > 80 and total_leads > 10:
        risk += 20

    # deals without visit
    deals_no_visit = Deal.objects.filter(agent=agent, status=Deal.Status.WON, lead__site_visits__isnull=True).count()
    if deals_no_visit > 0:
        risk += 30
        notes["deals_no_visit"] = deals_no_visit

    # wallet spike last 24h
    since = timezone.now() - timedelta(hours=24)
    spike = (
        WalletTransaction.objects.filter(agent=agent, created_at__gte=since, type=WalletTransaction.Type.CREDIT)
        .aggregate(total=Decimal("0.00"))["total"]
    )
    if spike and spike > Decimal("50000"):
        risk += 15
        notes["wallet_spike"] = float(spike)

    # response delay: leads with no contact in 24h
    stalled = Lead.objects.filter(assigned_agent=agent, last_contacted_at__isnull=True, created_at__lt=timezone.now() - timedelta(days=1)).count()
    if stalled > 5:
        risk += 10
        notes["stalled_leads"] = stalled

    # location mismatch: completed visits with distance_mismatch >0.5 km
    mismatches = SiteVisit.objects.filter(agent=agent, distance_mismatch__gt=0.5, status=SiteVisit.Status.COMPLETED).count()
    if mismatches:
        risk += 25
        notes["location_mismatch"] = mismatches

    risk = max(0, min(100, risk))
    level = AgentRiskProfile.RiskLevel.LOW
    if risk >= 71:
        level = AgentRiskProfile.RiskLevel.HIGH
    elif risk >= 31:
        level = AgentRiskProfile.RiskLevel.MEDIUM

    profile, _ = AgentRiskProfile.objects.get_or_create(agent=agent)
    profile.risk_score = risk
    profile.risk_level = level
    profile.last_evaluated = timezone.now()
    profile.notes = notes
    profile.save(update_fields=["risk_score", "risk_level", "last_evaluated", "notes"])

    if level == AgentRiskProfile.RiskLevel.HIGH:
        agent.under_review = True
        agent.save(update_fields=["under_review", "updated_at"])
    return profile


def evaluate_all_agents():
    for agent in Agent.objects.filter(is_active=True):
        calculate_risk(agent)
