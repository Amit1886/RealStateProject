from datetime import timedelta
from threading import Lock

from django.db.utils import OperationalError
from django.db import transaction
from django.utils import timezone

from billing.models import (
    Plan,
    Subscription,
    FeatureRegistry,
    PlanFeature,
    SubscriptionHistory,
    UserFeatureOverride,
)


FEATURE_REGISTRY = [
    {"key": "billing.invoices", "label": "Invoices", "group": "Billing"},
    {"key": "billing.returns", "label": "Returns", "group": "Billing"},
    {"key": "billing.credit_notes", "label": "Credit Notes", "group": "Billing"},
    {"key": "commerce.orders", "label": "Orders", "group": "Commerce"},
    {"key": "commerce.purchase", "label": "Purchase", "group": "Commerce"},
    {"key": "commerce.suppliers", "label": "Suppliers", "group": "Commerce"},
    {"key": "commerce.inventory", "label": "Inventory", "group": "Inventory"},
    {"key": "inventory.barcode", "label": "Barcode", "group": "Inventory"},
    {"key": "barcode.print", "label": "Barcode Print", "group": "Inventory"},
    {"key": "inventory.batch", "label": "Batch", "group": "Inventory"},
    {"key": "inventory.expiry", "label": "Expiry", "group": "Inventory"},
    {"key": "communication.whatsapp", "label": "WhatsApp Bot", "group": "Communication"},
    {"key": "whatsapp.orders", "label": "WhatsApp Orders", "group": "Communication"},
    {"key": "communication.sms", "label": "SMS", "group": "Communication"},
    {"key": "communication.email", "label": "Email", "group": "Communication"},
    {"key": "advanced.ai_reports", "label": "AI Reports", "group": "Advanced"},
    {"key": "advanced.api", "label": "API Access", "group": "Advanced"},
    {"key": "api.access", "label": "API Access", "group": "Advanced"},
    {"key": "advanced.automation", "label": "Automation", "group": "Advanced"},
    {"key": "settings.advanced", "label": "Advanced Settings", "group": "Advanced"},
    {"key": "multiuser", "label": "Multi-user", "group": "Advanced"},
    {"key": "reports.advanced", "label": "Advanced Reports", "group": "Advanced"},
    {"key": "payments.gateway", "label": "Payment Gateway", "group": "Advanced"},
    {"key": "field.agents", "label": "Field Agents", "group": "Advanced"},
    {"key": "chatbot.flows", "label": "Chatbot Flows", "group": "Communication"},
]


_registry_sync_lock = Lock()
_registry_synced = False


def sync_feature_registry():
    """
    Ensure FeatureRegistry/PlanFeature rows exist.

    Important: this function writes to DB. It must not be called repeatedly per-request
    (especially on SQLite). It is safe to call on-demand; it will run at most once
    per-process and is resilient to transient SQLite lock errors.
    """
    global _registry_synced
    if _registry_synced:
        return

    with _registry_sync_lock:
        if _registry_synced:
            return

        try:
            desired_keys = [x["key"] for x in FEATURE_REGISTRY]
            existing_keys = set(
                FeatureRegistry.objects.filter(key__in=desired_keys).values_list("key", flat=True)
            )
            needs_sync = len(existing_keys) != len(desired_keys)
            if not needs_sync:
                _registry_synced = True
                return

            for index, item in enumerate(FEATURE_REGISTRY):
                FeatureRegistry.objects.update_or_create(
                    key=item["key"],
                    defaults={
                        "label": item["label"],
                        "group": item.get("group", "General"),
                        "description": item.get("description", ""),
                        "sort_order": index,
                        "active": True,
                    },
                )
            # Ensure every plan has entries for newly added features
            for plan in Plan.objects.all():
                for feature in FeatureRegistry.objects.filter(active=True):
                    PlanFeature.objects.get_or_create(plan=plan, feature=feature, defaults={"enabled": True})

            _registry_synced = True
        except OperationalError:
            # SQLite can throw "database is locked" under concurrent access.
            # Don't crash templates/pages; callers should behave read-only on failure.
            return


def get_active_subscription(user):
    return Subscription.objects.filter(user=user, status="active").select_related("plan").first()


def user_has_feature(user, feature_key):
    if user.is_superuser:
        return True
    try:
        sync_feature_registry()
    except OperationalError:
        pass
    override = UserFeatureOverride.objects.filter(
        user=user, feature__key=feature_key
    ).select_related("feature").first()
    if override is not None:
        return override.is_enabled
    subscription = get_active_subscription(user)
    if not subscription or not subscription.plan:
        return False
    return PlanFeature.objects.filter(plan=subscription.plan, feature__key=feature_key, enabled=True).exists()


def get_locked_feature_count(user):
    try:
        sync_feature_registry()
    except OperationalError:
        pass
    subscription = get_active_subscription(user)
    if not subscription or not subscription.plan:
        return FeatureRegistry.objects.filter(active=True).count()
    enabled_keys = PlanFeature.objects.filter(plan=subscription.plan, enabled=True).values_list("feature__key", flat=True)
    return FeatureRegistry.objects.filter(active=True).exclude(key__in=enabled_keys).count()


def get_usage_summary(user):
    # Placeholder for usage meters; can be expanded later.
    return {
        "usage": 12,
        "limit": 100,
    }


@transaction.atomic
def ensure_free_plan(user):
    free_plan = Plan.objects.filter(price_monthly=0, price_yearly=0, active=True).order_by("id").first()
    if not free_plan:
        free_plan = Plan.objects.create(
            name="Free",
            price=0,
            price_monthly=0,
            price_yearly=0,
            trial_days=0,
            active=True,
        )
    try:
        if hasattr(user, "userprofile") and user.userprofile:
            user.userprofile.plan = free_plan
            user.userprofile.save(update_fields=["plan"])
    except Exception:
        pass
    subscription = Subscription.objects.filter(user=user, status="active").first()
    if not subscription:
        subscription = Subscription.objects.create(
            user=user,
            plan=free_plan,
            status="active",
            start_date=timezone.now(),
        )
        SubscriptionHistory.objects.create(
            user=user,
            plan=free_plan,
            event_type="created",
            details={"source": "auto_free_plan"},
        )
    return subscription


def upgrade_subscription(user, plan):
    subscription = Subscription.objects.filter(user=user).order_by("-created_at").first()
    if subscription:
        subscription.plan = plan
        subscription.status = "active"
        subscription.start_date = timezone.now()
        if plan.trial_days:
            subscription.trial_end = timezone.now() + timedelta(days=plan.trial_days)
        subscription.save()
    else:
        subscription = Subscription.objects.create(
            user=user,
            plan=plan,
            status="active",
            start_date=timezone.now(),
        )
    SubscriptionHistory.objects.create(
        user=user,
        plan=plan,
        event_type="upgraded",
        details={"source": "upgrade_flow"},
    )
    return subscription
