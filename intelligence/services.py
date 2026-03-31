from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Avg, Count, Q
from django.utils.dateparse import parse_datetime
from django.utils import timezone

from communication.services import queue_notification_event
from fraud_detection.services import raise_signal
from intelligence.models import (
    AggregatedProperty,
    DemandHeatmapSnapshot,
    InvestorMatch,
    InvestorProfile,
    LeadPurchase,
    PremiumLeadListing,
    PriceTrendSnapshot,
    PropertyAlertSubscription,
    PropertyImportBatch,
)
from leads.models import Lead, Property, PropertyProject, PropertyView
from leads.services import assign_lead
from wallet.services import debit, get_or_create_wallet


def _json_safe(value):
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value


def normalize_property_payload(payload: dict) -> dict:
    title = str(payload.get("title") or "").strip()
    location = str(payload.get("location") or payload.get("address") or "").strip()
    city = str(payload.get("city") or "").strip()
    district = str(payload.get("district") or "").strip()
    state = str(payload.get("state") or "").strip()
    pin_code = str(payload.get("pin_code") or payload.get("pincode") or "").strip()
    property_type = str(payload.get("property_type") or "").strip().lower()
    area = payload.get("area_sqft") or payload.get("area") or payload.get("area_size")
    price = payload.get("price") or 0
    source = str(payload.get("source") or "aggregator").strip()
    source_reference = str(payload.get("source_reference") or payload.get("external_id") or "").strip()
    import_date = payload.get("import_date") or timezone.now()
    if isinstance(import_date, str):
        import_date = parse_datetime(import_date) or timezone.now()
    normalized_title = " ".join(title.lower().split())
    duplicate_key = build_duplicate_key(
        title=normalized_title,
        location=location.lower(),
        price=price,
        property_type=property_type,
        area=area or "",
    )
    enrichment = {
        "normalized_location": location.title(),
        "investment_tag": payload.get("investment_tag") or "standard",
        "estimated_roi_percent": str(payload.get("estimated_roi_percent") or payload.get("roi_percent") or "0"),
    }
    return {
        "title": title,
        "normalized_title": normalized_title,
        "location": location,
        "city": city,
        "district": district,
        "state": state,
        "pin_code": pin_code,
        "property_type": property_type,
        "area_sqft": area,
        "price": Decimal(str(price or 0)),
        "source": source,
        "source_reference": source_reference,
        "import_date": import_date,
        "duplicate_key": duplicate_key,
        "enrichment_data": enrichment,
    }


def build_duplicate_key(*, title: str, location: str, price, property_type: str, area) -> str:
    raw = f"{title}|{location}|{property_type}|{price}|{area}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:48]


def _find_existing_property(company, normalized: dict) -> Property | None:
    qs = Property.objects.filter(
        Q(company=company) | Q(company__isnull=True),
        title__iexact=normalized["title"],
        city__iexact=normalized["city"],
        property_type=normalized["property_type"] or Property.Type.APARTMENT,
    )
    if normalized["pin_code"]:
        qs = qs.filter(pin_code=normalized["pin_code"])
    if normalized["price"]:
        qs = qs.filter(price=normalized["price"])
    return qs.first()


@transaction.atomic
def ingest_aggregated_listing(payload: dict, *, batch: PropertyImportBatch | None = None, company=None):
    normalized = normalize_property_payload(payload)
    duplicate_of = AggregatedProperty.objects.filter(
        company=company,
        duplicate_key=normalized["duplicate_key"],
        is_duplicate=False,
    ).first()
    matched_property = duplicate_of.matched_property if duplicate_of else _find_existing_property(company, normalized)
    is_duplicate = duplicate_of is not None

    if not matched_property and not is_duplicate:
        matched_property = Property.objects.create(
            company=company,
            title=normalized["title"][:200] or "Aggregated Property",
            location=normalized["location"][:160],
            city=normalized["city"][:120] or "Unknown",
            district=normalized["district"][:120],
            state=normalized["state"][:120],
            pin_code=normalized["pin_code"][:12],
            price=normalized["price"],
            property_type=(normalized["property_type"] or Property.Type.APARTMENT)[:20],
            area_sqft=normalized["area_sqft"] or None,
            status=Property.Status.APPROVED,
            aggregated_property=True,
            data_source=normalized["source"][:120],
            import_date=normalized["import_date"],
            source_reference=normalized["source_reference"][:160],
            metadata={
                "aggregation_enrichment": normalized["enrichment_data"],
                "aggregated": True,
            },
        )

    agg = AggregatedProperty.objects.create(
        company=company,
        import_batch=batch,
        matched_property=matched_property,
        duplicate_of=duplicate_of,
        source=normalized["source"],
        source_reference=normalized["source_reference"],
        title=normalized["title"],
        normalized_title=normalized["normalized_title"],
        location=normalized["location"],
        city=normalized["city"],
        district=normalized["district"],
        state=normalized["state"],
        pin_code=normalized["pin_code"],
        price=normalized["price"],
        property_type=normalized["property_type"],
        area_sqft=normalized["area_sqft"] or None,
        duplicate_key=normalized["duplicate_key"],
        is_duplicate=is_duplicate,
        import_date=normalized["import_date"],
        raw_payload=_json_safe(payload),
        normalized_payload=_json_safe(normalized),
        enrichment_data=_json_safe(normalized["enrichment_data"]),
    )

    if is_duplicate:
        raise_signal(
            signal_type="duplicate_property_listing",
            severity="medium",
            description=f"Duplicate aggregated property detected for {normalized['title']}",
            payload={"duplicate_key": normalized["duplicate_key"], "aggregated_property_id": agg.id},
        )

    return agg


def run_import_batch(batch: PropertyImportBatch, records: list[dict]):
    batch.status = PropertyImportBatch.Status.RUNNING
    batch.started_at = timezone.now()
    batch.fetched_count = len(records)
    batch.save(update_fields=["status", "started_at", "fetched_count", "updated_at"])
    inserted = 0
    duplicates = 0
    for record in records:
        agg = ingest_aggregated_listing(record, batch=batch, company=batch.company)
        inserted += 1
        if agg.is_duplicate:
            duplicates += 1
    batch.inserted_count = inserted
    batch.duplicate_count = duplicates
    batch.normalized_count = inserted
    batch.status = PropertyImportBatch.Status.COMPLETED
    batch.completed_at = timezone.now()
    batch.save(
        update_fields=[
            "inserted_count",
            "duplicate_count",
            "normalized_count",
            "status",
            "completed_at",
            "updated_at",
        ]
    )
    return batch


def refresh_demand_heatmap(company=None, snapshot_date=None):
    snapshot_date = snapshot_date or timezone.localdate()
    demand_rows = defaultdict(lambda: {"lead_count": 0, "search_count": 0, "property_view_count": 0, "closed_deal_count": 0, "supply_count": 0})

    leads = Lead.objects.filter(created_at__date=snapshot_date)
    if company:
        leads = leads.filter(Q(company=company) | Q(company__isnull=True))
    for row in leads.values("city", "district").annotate(c=Count("id")):
        key = (row["city"] or "", row["district"] or "")
        demand_rows[key]["lead_count"] = row["c"]
        demand_rows[key]["search_count"] = row["c"]

    views = PropertyView.objects.filter(timestamp__date=snapshot_date)
    if company:
        views = views.filter(Q(property__company=company) | Q(property__company__isnull=True))
    for row in views.values("property__city", "property__district").annotate(c=Count("id")):
        key = (row["property__city"] or "", row["property__district"] or "")
        demand_rows[key]["property_view_count"] = row["c"]

    deals = Lead.objects.filter(status=Lead.Status.CLOSED, updated_at__date=snapshot_date)
    if company:
        deals = deals.filter(Q(company=company) | Q(company__isnull=True))
    for row in deals.values("city", "district").annotate(c=Count("id")):
        key = (row["city"] or "", row["district"] or "")
        demand_rows[key]["closed_deal_count"] = row["c"]

    supply = Property.objects.exclude(status=Property.Status.REJECTED)
    if company:
        supply = supply.filter(Q(company=company) | Q(company__isnull=True))
    for row in supply.values("city", "district").annotate(c=Count("id")):
        key = (row["city"] or "", row["district"] or "")
        demand_rows[key]["supply_count"] = row["c"]

    created = []
    for (city, district), values in demand_rows.items():
        demand_score = Decimal(values["lead_count"] * 2 + values["property_view_count"] + values["closed_deal_count"] * 3)
        supply_count = values["supply_count"] or 1
        low_supply_score = Decimal(max(0, values["lead_count"] - supply_count))
        hot_investment_score = Decimal((demand_score / Decimal(str(supply_count))).quantize(Decimal("0.01")))
        snapshot, _ = DemandHeatmapSnapshot.objects.update_or_create(
            company=company,
            snapshot_date=snapshot_date,
            city=city,
            district=district,
            defaults={
                **values,
                "demand_score": demand_score,
                "low_supply_score": low_supply_score,
                "hot_investment_score": hot_investment_score,
                "payload": {
                    "high_demand_zone": demand_score >= 10,
                    "low_supply_area": low_supply_score > 0,
                    "hot_investment_location": hot_investment_score >= 2,
                },
            },
        )
        created.append(snapshot)
    return created


def refresh_price_trends(company=None, snapshot_date=None):
    snapshot_date = snapshot_date or timezone.localdate()
    qs = Property.objects.exclude(status=Property.Status.REJECTED)
    if company:
        qs = qs.filter(Q(company=company) | Q(company__isnull=True))
    rows = qs.values("city", "district", "property_type").annotate(avg_price=Avg("price"), count=Count("id"))
    results = []
    for row in rows:
        previous = PriceTrendSnapshot.objects.filter(
            company=company,
            city=row["city"] or "",
            district=row["district"] or "",
            property_type=row["property_type"] or "",
        ).exclude(snapshot_date=snapshot_date).order_by("-snapshot_date").first()
        current_avg = Decimal(str(row["avg_price"] or 0))
        prev_avg = previous.average_price if previous else Decimal("0.00")
        change_percent = Decimal("0.00")
        if prev_avg:
            change_percent = ((current_avg - prev_avg) / prev_avg) * Decimal("100.00")
        trend, _ = PriceTrendSnapshot.objects.update_or_create(
            company=company,
            snapshot_date=snapshot_date,
            city=row["city"] or "",
            district=row["district"] or "",
            property_type=row["property_type"] or "",
            defaults={
                "average_price": current_avg,
                "price_change_percent": change_percent.quantize(Decimal("0.01")),
                "historical_prices": ([float(prev_avg)] if prev_avg else []) + [float(current_avg)],
                "sample_size": row["count"],
            },
        )
        results.append(trend)
    return results


def _roi_for_property(property_obj: Property) -> Decimal:
    meta = property_obj.metadata or {}
    return Decimal(str(meta.get("expected_roi_percent") or meta.get("aggregation_enrichment", {}).get("estimated_roi_percent") or 10))


def _match_score_for_investor(investor: InvestorProfile, *, property_obj: Property | None = None, project: PropertyProject | None = None):
    target_city = property_obj.city if property_obj else project.city
    target_type = property_obj.property_type if property_obj else ((project.property_types or [""])[0] if project and project.property_types else "")
    target_price = property_obj.price if property_obj else Decimal(str(project.starting_price or 0))
    target_roi = _roi_for_property(property_obj) if property_obj else Decimal(str(project.roi_percent or 0))
    score = Decimal("0.00")
    reasons = []
    preferred_cities = {str(city).strip().lower() for city in (investor.preferred_cities or [])}
    preferred_types = {str(value).strip().lower() for value in (investor.property_type_preferences or [])}
    if target_city and target_city.lower() in preferred_cities:
        score += Decimal("35")
        reasons.append("preferred city")
    if target_type and target_type.lower() in preferred_types:
        score += Decimal("20")
        reasons.append("preferred property type")
    if target_price and investor.investment_budget and target_price <= investor.investment_budget:
        score += Decimal("25")
        reasons.append("within budget")
    if target_roi and target_roi >= investor.min_roi_percent:
        score += Decimal("20")
        reasons.append("roi threshold")
    return score, target_roi, ", ".join(reasons)


def refresh_investor_matches_for_property(property_obj: Property):
    matches = []
    investors = InvestorProfile.objects.filter(active=True)
    for investor in investors:
        score, roi, reason = _match_score_for_investor(investor, property_obj=property_obj)
        if score < Decimal("40"):
            continue
        match, _ = InvestorMatch.objects.update_or_create(
            investor=investor,
            property=property_obj,
            project=None,
            defaults={
                "score": score,
                "expected_roi_percent": roi,
                "match_reason": reason,
                "payload": {"source": "property"},
            },
        )
        matches.append(match)
    return matches


def refresh_investor_matches_for_project(project: PropertyProject):
    matches = []
    investors = InvestorProfile.objects.filter(active=True)
    for investor in investors:
        score, roi, reason = _match_score_for_investor(investor, project=project)
        if score < Decimal("40"):
            continue
        match, _ = InvestorMatch.objects.update_or_create(
            investor=investor,
            property=None,
            project=project,
            defaults={
                "score": score,
                "expected_roi_percent": roi,
                "match_reason": reason or "builder project opportunity",
                "payload": {"source": "project"},
            },
        )
        matches.append(match)
    return matches


def dispatch_investor_match_alert(match: InvestorMatch):
    investor = match.investor
    if not investor.alerts_enabled:
        return None
    title = "New investment opportunity"
    subject = match.property.title if match.property else match.project.title
    body = f"{subject} matched your portfolio with score {match.score}."
    result = queue_notification_event(
        users=[investor.user] if investor.user_id else [],
        title=title,
        body=body,
        channels=["in_app", "email", "whatsapp"],
        email=investor.email,
        whatsapp_number=investor.phone,
        metadata={"investor_match_id": match.id},
    )
    match.status = InvestorMatch.Status.NOTIFIED
    match.notified_at = timezone.now()
    match.save(update_fields=["status", "notified_at", "updated_at"])
    return result


def _subscription_matches_property(subscription: PropertyAlertSubscription, property_obj: Property, trigger: str):
    triggers = subscription.trigger_types or ["new_property"]
    if trigger not in triggers:
        return False
    if subscription.city and subscription.city.lower() != (property_obj.city or "").lower():
        return False
    if subscription.district and subscription.district.lower() != (property_obj.district or "").lower():
        return False
    if subscription.pin_code and subscription.pin_code != (property_obj.pin_code or ""):
        return False
    if subscription.property_type and subscription.property_type != property_obj.property_type:
        return False
    if subscription.min_budget and property_obj.price < subscription.min_budget:
        return False
    if subscription.max_budget and property_obj.price > subscription.max_budget:
        return False
    return True


def dispatch_property_alerts_for_property(property_obj: Property, *, trigger: str = "new_property"):
    subs = PropertyAlertSubscription.objects.filter(is_active=True)
    results = []
    for subscription in subs.select_related("customer", "customer__user"):
        if not _subscription_matches_property(subscription, property_obj, trigger):
            continue
        user = subscription.customer.user
        channels = subscription.channels or ["in_app"]
        result = queue_notification_event(
            users=[user],
            title="Property alert",
            body=f"{property_obj.title} is available in {property_obj.city}.",
            channels=channels,
            email=user.email,
            phone=user.mobile or "",
            whatsapp_number=user.mobile or "",
            metadata={"property_id": property_obj.id, "trigger": trigger},
        )
        results.append(result)
    return results


def dispatch_builder_launch_alert(project: PropertyProject):
    subs = PropertyAlertSubscription.objects.filter(is_active=True)
    results = []
    for subscription in subs.select_related("customer", "customer__user"):
        triggers = subscription.trigger_types or []
        if "builder_launch" not in triggers:
            continue
        if subscription.city and subscription.city.lower() != (project.city or "").lower():
            continue
        user = subscription.customer.user
        results.append(
            queue_notification_event(
                users=[user],
                title="Builder launch alert",
                body=f"New builder project launched: {project.title} in {project.city}.",
                channels=subscription.channels or ["in_app"],
                email=user.email,
                whatsapp_number=user.mobile or "",
                metadata={"project_id": project.id, "trigger": "builder_launch"},
            )
        )
    return results


@transaction.atomic
def purchase_lead_listing(listing: PremiumLeadListing, *, buyer_agent, actor_user=None):
    if listing.status != PremiumLeadListing.Status.AVAILABLE:
        raise ValueError("Lead listing is not available")
    wallet = get_or_create_wallet(buyer_agent.user)
    if wallet.balance < listing.price:
        raise ValueError("Insufficient wallet balance")
    debit(buyer_agent.user, listing.price, source="premium_lead_purchase", reference=f"lead-listing:{listing.id}")
    assign_lead(
        listing.lead,
        agent=buyer_agent,
        actor=actor_user or buyer_agent.user,
        reason="Purchased from lead marketplace",
        match_level="manual",
        assignment_type="manual",
    )
    listing.status = PremiumLeadListing.Status.SOLD
    listing.buyer_agent = buyer_agent
    listing.save(update_fields=["status", "buyer_agent", "updated_at"])
    purchase = LeadPurchase.objects.create(
        listing=listing,
        lead=listing.lead,
        buyer_agent=buyer_agent,
        amount=listing.price,
        wallet_transaction_ref=f"lead-listing:{listing.id}",
    )
    return purchase


def evaluate_spam_lead(lead: Lead):
    recent_count = Lead.objects.filter(mobile=lead.mobile, created_at__gte=timezone.now() - timedelta(days=1)).count()
    if lead.mobile and recent_count >= 4:
        return raise_signal(
            signal_type="spam_lead",
            user=lead.created_by,
            severity="high",
            description=f"Multiple leads detected from {lead.mobile}",
            payload={"lead_id": lead.id, "count_24h": recent_count},
        )
    return None


def evaluate_fake_agent(agent):
    if getattr(agent, "approval_status", "") == "approved" and not getattr(agent, "license_number", ""):
        return raise_signal(
            signal_type="fake_agent_suspected",
            user=getattr(agent, "user", None),
            severity="medium",
            description=f"Approved agent {agent.id} has no license number",
            payload={"agent_id": agent.id},
        )
    return None
