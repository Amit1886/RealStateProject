import logging
from typing import Any, Dict

from django.db import transaction

from addons.autopilot_engine.models import AutopilotAuditLog

logger = logging.getLogger(__name__)


class ActionExecutionError(Exception):
    pass


class ActionRegistry:
    def __init__(self):
        self._registry = {}

    def register(self, key):
        def decorator(func):
            self._registry[key] = func
            return func

        return decorator

    def execute(self, key: str, context: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        if key not in self._registry:
            raise ActionExecutionError(f"Unknown action: {key}")
        return self._registry[key](context=context, params=params)


registry = ActionRegistry()


def _audit(context: Dict[str, Any], action: str, meta: Dict[str, Any]):
    event = context["event"]
    AutopilotAuditLog.objects.create(
        actor=event.actor,
        action=action,
        target=str(event.id),
        branch_code=event.branch_code,
        meta=meta,
    )


@registry.register("generate_invoice")
def action_generate_invoice(context: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    # Placeholder service wrapper for legacy billing integration.
    _audit(context, "generate_invoice", params)
    return {"result": "queued", "action": "generate_invoice"}


@registry.register("reduce_stock")
def action_reduce_stock(context: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    # Safe by default: this addon does not mutate legacy inventory unless explicitly enabled.
    dry_run = params.get("dry_run", True)
    _audit(context, "reduce_stock", {"dry_run": dry_run})
    return {"result": "noop" if dry_run else "queued", "action": "reduce_stock"}


@registry.register("assign_courier")
def action_assign_courier(context: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    provider = params.get("provider", "shiprocket")
    use_addon = bool(params.get("use_addon", False))

    if not use_addon:
        _audit(context, "assign_courier", {"provider": provider, "mode": "legacy_placeholder"})
        return {"result": "queued", "provider": provider}

    event = context["event"]
    storefront_order_id = (event.payload or {}).get("storefront_order_id")
    order_number = (event.payload or {}).get("order_number")
    ref = str(order_number or storefront_order_id or "")
    if not ref:
        raise ActionExecutionError("missing storefront_order reference in event payload")

    try:
        from addons.courier_integration.services import create_shipment

        shipment = create_shipment(
            branch_code=event.branch_code,
            provider=provider,
            ref_type=params.get("ref_type", "storefront_order"),
            ref=ref,
            payload={"autopilot_event_id": event.id},
        )
        _audit(context, "assign_courier", {"provider": provider, "shipment_id": shipment.id, "awb": shipment.awb})
        return {"result": "done", "provider": provider, "shipment_id": shipment.id, "awb": shipment.awb}
    except ActionExecutionError:
        raise
    except Exception as exc:
        raise ActionExecutionError(f"assign_courier_failed:{exc}")


@registry.register("send_sms")
def action_send_sms(context: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    _audit(context, "send_sms", {"template": params.get("template", "order_update")})
    return {"result": "queued"}


@registry.register("update_ledger")
def action_update_ledger(context: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    _audit(context, "update_ledger", params)
    return {"result": "queued"}


@registry.register("notify_customer")
def action_notify_customer(context: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    channel = params.get("channel", "whatsapp")
    _audit(context, "notify_customer", {"channel": channel})
    return {"result": "queued", "channel": channel}


@registry.register("run_backup")
def action_run_backup(context: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    from addons.autopilot_engine.models import BackupJob

    job = BackupJob.objects.create(
        storage=params.get("storage", "local"),
        snapshot_ref=params.get("snapshot_ref", "pending"),
        details=params,
    )
    _audit(context, "run_backup", {"backup_job_id": job.id})
    return {"result": "queued", "backup_job_id": job.id}


@registry.register("ecommerce_sync_to_billing")
def action_ecommerce_sync_to_billing(context: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
    event = context["event"]
    storefront_order_id = (event.payload or {}).get("storefront_order_id")
    if not storefront_order_id:
        raise ActionExecutionError("missing storefront_order_id in event payload")

    try:
        from addons.ecommerce_engine.models import StorefrontOrder
        from addons.ecommerce_engine.services import sync_order_back_to_billing

        order = StorefrontOrder.objects.filter(id=storefront_order_id).first()
        if not order:
            raise ActionExecutionError("storefront order not found")
        sync_order_back_to_billing(order)
        _audit(context, "ecommerce_sync_to_billing", {"order_id": order.id, "order_number": order.order_number})
        return {"result": "done", "order_id": order.id}
    except ActionExecutionError:
        raise
    except Exception as exc:
        raise ActionExecutionError(f"ecommerce_sync_failed:{exc}")
