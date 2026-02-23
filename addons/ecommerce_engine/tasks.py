from celery import shared_task

from addons.ecommerce_engine.models import StorefrontOrder
from addons.ecommerce_engine.services import sync_order_back_to_billing


@shared_task
def sync_storefront_order_to_billing(order_id: int):
    order = StorefrontOrder.objects.filter(id=order_id).first()
    if not order:
        return
    if order.synced_to_billing:
        return
    sync_order_back_to_billing(order)
