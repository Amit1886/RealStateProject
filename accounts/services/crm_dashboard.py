from __future__ import annotations

from decimal import Decimal

from django.core.cache import cache
from django.db.models import Q, Sum
from django.utils import timezone


def resolve_crm_role(user) -> str:
    if not getattr(user, "is_authenticated", False):
        return "customer"
    if user.is_superuser or user.is_staff:
        return "admin"
    if getattr(user, "agent_profile", None):
        return "agent"
    return "customer"


def _scope_company(queryset, company):
    if company is None:
        return queryset
    field_names = {field.name for field in queryset.model._meta.get_fields()}
    if "company" not in field_names:
        return queryset
    return queryset.filter(company=company)


def _crm_dashboard_cache_key(user) -> str:
    agent_profile = getattr(user, "agent_profile", None)
    company = getattr(user, "company", None)
    return ":".join(
        [
            "crm_dashboard",
            str(getattr(user, "pk", "anon")),
            resolve_crm_role(user),
            str(getattr(company, "pk", "none")),
            str(getattr(agent_profile, "pk", "none")),
        ]
    )


def build_crm_dashboard_context(user, refresh=False):
    default_context = {
        "role": resolve_crm_role(user),
        "snapshot": {
            "total_leads": 0,
            "conversion_rate": 0,
            "active_conversations": 0,
            "duplicates": 0,
            "unassigned_leads": 0,
            "followups_due": 0,
            "pending_response_count": 0,
        },
        "total_leads": 0,
        "total_properties": 0,
        "total_customers": 0,
        "active_agents": 0,
        "auto_assigned_count": 0,
        "unassigned_leads": 0,
        "followups_due": 0,
        "converted_leads": 0,
        "closed_leads": 0,
        "duplicate_leads": 0,
        "open_deals": 0,
        "won_deals": 0,
        "pending_payout_count": 0,
        "pending_payout_total": Decimal("0.00"),
        "inbound_revenue": Decimal("0.00"),
        "active_conversations": 0,
        "import_batch_count": 0,
        "nearby_property_count": 0,
        "total_commission": Decimal("0.00"),
        "assigned_agent": None,
        "recent_import_batches": [],
        "recent_assignments": [],
        "recent_conversations": [],
        "recent_deals": [],
        "recent_leads": [],
        "recent_properties": [],
        "recent_agents": [],
        "recent_payments": [],
        "pipeline_rows": [],
    }
    if not getattr(user, "is_authenticated", False):
        return default_context

    cache_key = _crm_dashboard_cache_key(user)
    if not refresh:
        cached_context = cache.get(cache_key)
        if cached_context is not None:
            return cached_context

    try:
        from agents.models import Agent
        from customers.models import Customer
        from core_settings.models import CompanySettings
        from deals.models import Deal, Payment
        from leads.models import FollowUp, Lead, LeadActivity, LeadAssignment, LeadImportBatch, Property
        from leads.services import build_monitoring_snapshot
    except Exception:
        return default_context

    role = resolve_crm_role(user)
    agent_profile = getattr(user, "agent_profile", None)
    saas_company = getattr(user, "company", None)
    core_company = getattr(agent_profile, "company", None) or getattr(getattr(user, "userprofile", None), "company", None)
    if core_company is None and saas_company is not None:
        core_company = CompanySettings.objects.filter(company_name=saas_company.name).first()
    now = timezone.now()

    lead_qs = _scope_company(Lead.objects.all(), saas_company)
    property_qs = _scope_company(Property.objects.all(), saas_company)
    assignment_qs = LeadAssignment.objects.select_related("lead", "agent", "assigned_by")
    import_qs = _scope_company(
        LeadImportBatch.objects.select_related("source", "created_by"),
        saas_company,
    )
    conversation_qs = LeadActivity.objects.select_related("lead", "actor")
    deal_qs = _scope_company(
        Deal.objects.select_related("lead", "agent", "customer", "property"),
        saas_company,
    )
    payment_qs = _scope_company(
        Payment.objects.select_related("lead", "agent", "customer", "deal"),
        saas_company,
    )
    followup_qs = FollowUp.objects.select_related("lead")
    customer_qs = _scope_company(Customer.objects.select_related("user", "assigned_agent"), saas_company)
    agent_qs = _scope_company(Agent.objects.select_related("user"), core_company)

    if saas_company is not None:
        assignment_qs = assignment_qs.filter(lead__company=saas_company)
        conversation_qs = conversation_qs.filter(lead__company=saas_company)
        followup_qs = followup_qs.filter(lead__company=saas_company)

    customer_profile = None

    if role == "agent" and agent_profile:
        lead_qs = lead_qs.filter(Q(assigned_agent=agent_profile) | Q(assignments__agent=agent_profile)).distinct()
        property_qs = property_qs.filter(Q(assigned_agent=agent_profile) | Q(owner=user)).distinct()
        assignment_qs = assignment_qs.filter(agent=agent_profile)
        import_qs = import_qs.filter(Q(created_by=user) | Q(company=saas_company)).distinct()
        conversation_qs = conversation_qs.filter(
            Q(lead__assigned_agent=agent_profile) | Q(actor=user)
        ).distinct()
        deal_qs = deal_qs.filter(agent=agent_profile)
        payment_qs = payment_qs.filter(agent=agent_profile)
        followup_qs = followup_qs.filter(lead__assigned_agent=agent_profile)
        customer_qs = customer_qs.filter(assigned_agent=agent_profile)
        agent_qs = agent_qs.filter(pk=agent_profile.pk)
    elif role == "customer":
        customer_profile = customer_qs.filter(user=user).first()
        lead_scope = Q(created_by=user)
        if user.email:
            lead_scope |= Q(email__iexact=user.email)
        if customer_profile:
            lead_scope |= Q(converted_customer=customer_profile)
        lead_qs = lead_qs.filter(lead_scope).distinct()
        if customer_profile and customer_profile.assigned_agent_id:
            assignment_qs = assignment_qs.filter(agent=customer_profile.assigned_agent)
            agent_qs = agent_qs.filter(pk=customer_profile.assigned_agent_id)
        else:
            assignment_qs = assignment_qs.none()
            agent_qs = agent_qs.none()
        import_qs = import_qs.none()
        conversation_qs = conversation_qs.filter(
            Q(lead__in=lead_qs) | Q(actor=user)
        ).distinct()
        customer_scope = Q(lead__in=lead_qs)
        payment_scope = Q(lead__in=lead_qs)
        if customer_profile:
            customer_scope |= Q(customer=customer_profile)
            payment_scope |= Q(customer=customer_profile)
        deal_qs = deal_qs.filter(customer_scope).distinct()
        payment_qs = payment_qs.filter(payment_scope).distinct()
        followup_qs = followup_qs.filter(lead__in=lead_qs)
        customer_qs = customer_qs.filter(user=user)
        if customer_profile:
            property_scope = Q()
            has_property_scope = False
            if customer_profile.city:
                property_scope |= Q(city__iexact=customer_profile.city)
                has_property_scope = True
            if customer_profile.district:
                property_scope |= Q(district__iexact=customer_profile.district)
                has_property_scope = True
            if customer_profile.pin_code:
                property_scope |= Q(pin_code=customer_profile.pin_code)
                has_property_scope = True
            property_qs = property_qs.filter(property_scope).exclude(status=getattr(Property.Status, "REJECTED", "rejected")).distinct() if has_property_scope else property_qs.none()
        else:
            property_qs = property_qs.none()

    lead_qs = lead_qs.distinct()
    monitoring = build_monitoring_snapshot(lead_qs)
    conversation_types = ["whatsapp", "email", "sms", "call", "facebook_messenger", "instagram_dm"]
    active_conversations = conversation_qs.filter(activity_type__in=conversation_types).count()
    followups_due = followup_qs.filter(status=FollowUp.Status.PENDING, followup_date__lte=now).count()
    pending_response_count = assignment_qs.filter(is_active=True, response_due_at__lte=now, first_contact_at__isnull=True).count()
    converted_leads = lead_qs.filter(
        Q(status=Lead.Status.CONVERTED) | Q(stage=Lead.Stage.CONVERTED)
    ).count()
    closed_leads = lead_qs.filter(
        Q(status__in=[Lead.Status.CLOSED, Lead.Status.WON]) | Q(stage__in=[Lead.Stage.CLOSED, Lead.Stage.DEAL_CLOSED])
    ).count()
    pending_payout_qs = payment_qs.filter(
        direction=Payment.Direction.OUTBOUND,
        status__in=[Payment.Status.PENDING, Payment.Status.APPROVED],
    )
    inbound_revenue_qs = payment_qs.filter(
        direction=Payment.Direction.INBOUND,
        status__in=[Payment.Status.APPROVED, Payment.Status.PAID],
    )

    total_leads = lead_qs.count()
    total_properties = property_qs.count()
    total_customers = customer_qs.count()
    active_agents = agent_qs.filter(is_active=True).count()
    auto_assigned_count = assignment_qs.filter(assignment_type="auto").count()
    import_batch_count = import_qs.count()
    total_commission = deal_qs.aggregate(total=Sum("commission_amount"))["total"] or Decimal("0.00")
    pending_payout_total = pending_payout_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    inbound_revenue = inbound_revenue_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    total_for_percent = max(total_leads, 1)
    pipeline_rows = []
    stage_definitions = [
        ("New", Q(stage=Lead.Stage.NEW) | Q(status=Lead.Status.NEW), "crm"),
        ("Contacted", Q(stage=Lead.Stage.CONTACTED) | Q(status=Lead.Status.CONTACTED), "market"),
        ("Interested", Q(stage=Lead.Stage.INTERESTED), "info"),
        ("Site Visit", Q(stage__in=[Lead.Stage.SITE_VISIT, Lead.Stage.VISIT, Lead.Stage.VISIT_SCHEDULED]), "loan"),
        ("Negotiation", Q(stage=Lead.Stage.NEGOTIATION), "scheme"),
        ("Converted", Q(stage=Lead.Stage.CONVERTED) | Q(status=Lead.Status.CONVERTED), "content"),
        ("Closed", Q(stage__in=[Lead.Stage.CLOSED, Lead.Stage.DEAL_CLOSED]) | Q(status__in=[Lead.Status.CLOSED, Lead.Status.WON]), "intel"),
    ]
    for label, filters, tone in stage_definitions:
        count = lead_qs.filter(filters).distinct().count()
        pipeline_rows.append(
            {
                "label": label,
                "value": count,
                "percentage": int((count / total_for_percent) * 100) if total_for_percent else 0,
                "tone": tone,
            }
        )

    snapshot = {
        **monitoring,
        "active_conversations": active_conversations,
        "unassigned_leads": lead_qs.filter(assigned_agent__isnull=True).count(),
        "followups_due": followups_due,
        "pending_response_count": pending_response_count,
    }

    context = {
        "role": role,
        "snapshot": snapshot,
        "total_leads": total_leads,
        "total_properties": total_properties,
        "total_customers": total_customers,
        "active_agents": active_agents,
        "auto_assigned_count": auto_assigned_count,
        "unassigned_leads": snapshot["unassigned_leads"],
        "followups_due": followups_due,
        "converted_leads": converted_leads,
        "closed_leads": closed_leads,
        "duplicate_leads": snapshot.get("duplicates", 0),
        "open_deals": deal_qs.filter(status__in=[Deal.Status.DRAFT, Deal.Status.PENDING]).count(),
        "won_deals": deal_qs.filter(status=Deal.Status.WON).count(),
        "pending_payout_count": pending_payout_qs.count(),
        "pending_payout_total": pending_payout_total,
        "inbound_revenue": inbound_revenue,
        "active_conversations": active_conversations,
        "import_batch_count": import_batch_count,
        "nearby_property_count": property_qs.count(),
        "total_commission": total_commission,
        "assigned_agent": getattr(customer_profile, "assigned_agent", None),
        "recent_import_batches": list(import_qs.order_by("-created_at")[:5]),
        "recent_assignments": list(assignment_qs.order_by("-created_at")[:5]),
        "recent_conversations": list(
            conversation_qs.filter(activity_type__in=conversation_types).order_by("-created_at")[:5]
        ),
        "recent_deals": list(deal_qs.order_by("-updated_at")[:5]),
        "recent_leads": list(
            lead_qs.select_related("assigned_agent", "source_config", "converted_customer").order_by("-created_at")[:8]
        ),
        "recent_properties": list(
            property_qs.select_related("assigned_agent", "owner").order_by("-created_at")[:8]
        ),
        "recent_agents": list(agent_qs.order_by("-updated_at")[:8]),
        "recent_payments": list(payment_qs.order_by("-created_at")[:8]),
        "pipeline_rows": pipeline_rows,
    }
    cache.set(cache_key, context, 60)
    return context
