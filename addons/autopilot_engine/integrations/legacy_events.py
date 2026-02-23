from __future__ import annotations

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from addons.common.eventing import publish_event_safe

logger = logging.getLogger(__name__)


def _payload_for(instance, fields):
    data = {}
    for f in fields:
        try:
            val = getattr(instance, f, None)
            data[f] = str(val) if val is not None else None
        except Exception:
            data[f] = None
    return data


def _safe_sender_import(path: str):
    mod, name = path.rsplit(".", 1)
    try:
        module = __import__(mod, fromlist=[name])
        return getattr(module, name)
    except Exception:
        return None


CommerceInvoice = _safe_sender_import("commerce.models.Invoice")
CommerceOrder = _safe_sender_import("commerce.models.Order")
CommercePayment = _safe_sender_import("commerce.models.Payment")
BillingOrder = _safe_sender_import("billing.models.Order")
BillingPayment = _safe_sender_import("billing.models.Payment")
KhataTransaction = _safe_sender_import("khataapp.models.Transaction")


if CommerceInvoice is not None:

    @receiver(post_save, sender=CommerceInvoice)
    def commerce_invoice_events(sender, instance, created, **kwargs):
        publish_event_safe(
            event_key="commerce_invoice_created" if created else "commerce_invoice_updated",
            payload=_payload_for(
                instance,
                fields=[
                    "id",
                    "invoice_number",
                    "status",
                    "total_amount",
                    "created_at",
                ],
            ),
            source="commerce",
        )


if CommerceOrder is not None:

    @receiver(post_save, sender=CommerceOrder)
    def commerce_order_events(sender, instance, created, **kwargs):
        publish_event_safe(
            event_key="commerce_order_created" if created else "commerce_order_updated",
            payload=_payload_for(instance, fields=["id", "order_number", "status", "total_amount", "created_at"]),
            source="commerce",
        )


if CommercePayment is not None:

    @receiver(post_save, sender=CommercePayment)
    def commerce_payment_events(sender, instance, created, **kwargs):
        publish_event_safe(
            event_key="commerce_payment_created" if created else "commerce_payment_updated",
            payload=_payload_for(instance, fields=["id", "payment_ref", "status", "amount", "created_at"]),
            source="commerce",
        )


if BillingOrder is not None:

    @receiver(post_save, sender=BillingOrder)
    def billing_order_events(sender, instance, created, **kwargs):
        publish_event_safe(
            event_key="billing_order_created" if created else "billing_order_updated",
            payload=_payload_for(instance, fields=["id", "order_number", "status", "total_amount", "created_at"]),
            source="billing",
        )


if BillingPayment is not None:

    @receiver(post_save, sender=BillingPayment)
    def billing_payment_events(sender, instance, created, **kwargs):
        publish_event_safe(
            event_key="billing_payment_created" if created else "billing_payment_updated",
            payload=_payload_for(instance, fields=["id", "payment_ref", "status", "amount", "created_at"]),
            source="billing",
        )


if KhataTransaction is not None:

    @receiver(post_save, sender=KhataTransaction)
    def khata_transaction_events(sender, instance, created, **kwargs):
        publish_event_safe(
            event_key="khata_transaction_created" if created else "khata_transaction_updated",
            payload=_payload_for(instance, fields=["id", "txn_type", "amount", "created_at"]),
            source="khataapp",
        )

