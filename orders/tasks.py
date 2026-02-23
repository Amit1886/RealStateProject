from celery import shared_task

from orders.models import Order
from realtime.services.publisher import publish_event


@shared_task
def emit_order_event(order_id: int):
    order = Order.objects.filter(id=order_id).first()
    if not order:
        return {"status": "missing"}
    publish_event("live_orders", "order_updated", {"order_id": order_id, "status": order.status})
    return {"status": "ok"}
