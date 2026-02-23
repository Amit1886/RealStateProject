from django.db.models.signals import post_save
from django.dispatch import receiver

from addons.common.eventing import publish_event_safe

try:
    from orders.models import Order
except Exception:  # pragma: no cover
    Order = None


if Order is not None:

    @receiver(post_save, sender=Order)
    def autopilot_order_event(sender, instance, created, **kwargs):
        event_key = "order_created" if created else "order_updated"
        payload = {
            "order_id": getattr(instance, "id", None),
            "order_number": getattr(instance, "order_number", None),
            "status": getattr(instance, "status", None),
            "total_amount": str(getattr(instance, "total_amount", "")),
        }
        publish_event_safe(event_key=event_key, payload=payload, source="orders")
