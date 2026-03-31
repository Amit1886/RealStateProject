from __future__ import annotations

from leads.models import Lead
from leads.pipeline import calculate_closing_ratio, check_deadline_breach


def build_overdue_leads_report():
    check_deadline_breach()
    return Lead.objects.filter(is_overdue=True).select_related("assigned_agent", "assigned_to")

