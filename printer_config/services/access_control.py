from __future__ import annotations

from decimal import Decimal

from django.db.models import Count, Q

from billing.services import get_active_subscription
from printer_config.models import PrintTemplate


def _resolve_user_plan(user):
    subscription = get_active_subscription(user)
    if subscription and subscription.plan:
        return subscription.plan
    try:
        profile = getattr(user, "userprofile", None)
        if profile and profile.plan:
            return profile.plan
    except Exception:
        return None
    return None


def _is_basic_plan(plan) -> bool:
    if not plan:
        return True
    name = (plan.name or "").strip().lower()
    slug = (plan.slug or "").strip().lower()
    if any(token in {name, slug} for token in {"free", "basic"}):
        return True
    if "free" in name or "basic" in name or "free" in slug or "basic" in slug:
        return True
    monthly = getattr(plan, "price_monthly", Decimal("0.00")) or Decimal("0.00")
    yearly = getattr(plan, "price_yearly", Decimal("0.00")) or Decimal("0.00")
    return monthly == Decimal("0.00") and yearly == Decimal("0.00")


def allowed_templates_queryset(user, document_type: str | None = None):
    qs = PrintTemplate.objects.all()
    if document_type:
        qs = qs.filter(document_type=document_type)

    if user.is_superuser or user.is_staff:
        return qs

    qs = qs.filter(is_active=True, is_admin_approved=True, admin_only=False)
    plan = _resolve_user_plan(user)
    basic_plan = _is_basic_plan(plan)
    if basic_plan:
        qs = qs.filter(restrict_basic_plan=False)

    if not plan:
        return qs.filter(plan_access__isnull=True).distinct()

    qs = qs.annotate(
        plan_access_total=Count("plan_access", distinct=True),
        plan_access_allowed=Count(
            "plan_access",
            filter=Q(plan_access__plan=plan, plan_access__is_enabled=True),
            distinct=True,
        ),
    ).filter(Q(plan_access_total=0) | Q(plan_access_allowed__gt=0))

    return qs.distinct()


def select_default_template_for_user(user, document_type: str):
    qs = allowed_templates_queryset(user, document_type=document_type)
    picked = qs.filter(is_default=True).order_by("-updated_at", "id").first()
    if picked:
        return picked
    return qs.order_by("-updated_at", "id").first()
