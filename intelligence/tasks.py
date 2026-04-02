from __future__ import annotations

from django.utils import timezone

from intelligence.models import InvestorMatch, PremiumLeadListing, PropertyImportBatch
from intelligence.services import (
    dispatch_investor_match_alert,
    refresh_demand_heatmap,
    refresh_investor_matches_for_project,
    refresh_investor_matches_for_property,
    refresh_price_trends,
    run_import_batch,
)
from leads.models import Property, PropertyProject


try:
    from celery import shared_task
except ImportError:  # pragma: no cover - lightweight deployment fallback
    def shared_task(func=None, **kwargs):
        if func is None:
            def decorator(inner):
                inner.delay = inner
                inner.run = inner
                return inner

            return decorator

        func.delay = func
        func.run = func
        return func


@shared_task
def run_property_import_batch_task(batch_id: int):
    batch = PropertyImportBatch.objects.filter(id=batch_id).first()
    if not batch:
        return False
    records = list((batch.metadata or {}).get("records") or [])
    run_import_batch(batch, records)
    return True


@shared_task
def refresh_demand_heatmap_task(company_id=None):
    from saas_core.models import Company

    company = Company.objects.filter(id=company_id).first() if company_id else None
    refresh_demand_heatmap(company=company, snapshot_date=timezone.localdate())
    return True


@shared_task
def refresh_price_trends_task(company_id=None):
    from saas_core.models import Company

    company = Company.objects.filter(id=company_id).first() if company_id else None
    refresh_price_trends(company=company, snapshot_date=timezone.localdate())
    return True


@shared_task
def refresh_investor_matches_task():
    total = 0
    for property_obj in Property.objects.exclude(status=Property.Status.REJECTED).order_by("-created_at")[:300]:
        total += len(refresh_investor_matches_for_property(property_obj))
    for project in PropertyProject.objects.filter(approved=True).order_by("-created_at")[:300]:
        total += len(refresh_investor_matches_for_project(project))
    return total


@shared_task
def notify_pending_investor_matches_task():
    count = 0
    for match in InvestorMatch.objects.filter(status=InvestorMatch.Status.NEW).order_by("-score")[:200]:
        dispatch_investor_match_alert(match)
        count += 1
    return count


@shared_task
def expire_premium_leads_task():
    expired = PremiumLeadListing.objects.filter(status=PremiumLeadListing.Status.AVAILABLE, expires_at__lt=timezone.now())
    return expired.update(status=PremiumLeadListing.Status.EXPIRED)
