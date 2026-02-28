from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from billing.models import FeatureRegistry, PlanFeature, PlanPermissions


@dataclass(frozen=True)
class _PermRule:
    # When any of these permission fields are True, consider the module enabled.
    any_of: tuple[str, ...]
    feature_keys: tuple[str, ...]


_RULES: tuple[_PermRule, ...] = (
    _PermRule(
        any_of=("allow_add_party", "allow_edit_party", "allow_delete_party"),
        feature_keys=("commerce.suppliers",),
    ),
    _PermRule(
        any_of=("allow_add_transaction", "allow_edit_transaction", "allow_delete_transaction", "allow_bulk_transaction"),
        feature_keys=("billing.invoices", "billing.returns", "billing.credit_notes"),
    ),
    _PermRule(
        any_of=("allow_orders",),
        feature_keys=("commerce.orders", "commerce.purchase", "whatsapp.orders"),
    ),
    _PermRule(
        any_of=("allow_inventory",),
        feature_keys=(
            "commerce.inventory",
            "inventory.barcode",
            "barcode.print",
            "inventory.batch",
            "inventory.expiry",
        ),
    ),
    _PermRule(
        any_of=("allow_whatsapp",),
        feature_keys=("communication.whatsapp", "chatbot.flows"),
    ),
    _PermRule(
        any_of=("allow_sms",),
        feature_keys=("communication.sms",),
    ),
    _PermRule(
        any_of=("allow_email",),
        feature_keys=("communication.email",),
    ),
    _PermRule(
        any_of=("allow_reports",),
        feature_keys=("reports.advanced",),
    ),
    _PermRule(
        any_of=("allow_analytics",),
        feature_keys=("advanced.ai_reports", "advanced.automation"),
    ),
    _PermRule(
        any_of=("allow_settings",),
        feature_keys=("settings.advanced",),
    ),
    _PermRule(
        any_of=("allow_users",),
        feature_keys=("multiuser", "field.agents"),
    ),
    _PermRule(
        any_of=("allow_api_access",),
        feature_keys=("advanced.api", "api.access"),
    ),
    _PermRule(
        any_of=("allow_commerce",),
        feature_keys=("payments.gateway",),
    ),
)


def sync_plan_features_from_permissions(perms: PlanPermissions) -> int:
    """
    Make PlanFeature.enabled consistent with PlanPermissions toggles.

    This keeps UI gating (feature_allowed) aligned with plan-permission admin screens
    without changing existing templates/views.

    Returns the number of PlanFeature rows updated/created.
    """
    # Avoid accidental writes during migrations where tables may not be ready.
    if not perms or not perms.plan_id:
        return 0

    desired: dict[str, bool] = {}
    for rule in _RULES:
        allowed = any(bool(getattr(perms, f, False)) for f in rule.any_of)
        for key in rule.feature_keys:
            desired[key] = allowed

    if not desired:
        return 0

    features = {
        f.key: f for f in FeatureRegistry.objects.filter(key__in=list(desired.keys())).only("id", "key")
    }

    updated = 0
    with transaction.atomic():
        for key, allowed in desired.items():
            feature = features.get(key)
            if not feature:
                continue
            _, _created = PlanFeature.objects.update_or_create(
                plan=perms.plan,
                feature=feature,
                defaults={"enabled": allowed},
            )
            updated += 1
    return updated


@receiver(post_save, sender=PlanPermissions)
def _plan_permissions_post_save(sender, instance: PlanPermissions, created: bool, **kwargs):
    # On creation we avoid syncing to prevent surprising changes for existing deployments.
    # Sync will occur on explicit admin edits/saves and via the management command.
    if created:
        return
    try:
        sync_plan_features_from_permissions(instance)
    except Exception:
        # Never fail the admin save; this addon is best-effort.
        return

