from decimal import Decimal

from django.db import transaction

from addons.common.eventing import publish_event_safe
from addons.ecommerce_engine.models import StorefrontOrder, StorefrontOrderItem, StorefrontProduct, StorefrontSyncLog


@transaction.atomic
def sync_products_from_billing(branch_code: str = "default", only_selected_ids=None) -> int:
    from commerce.models import Product

    qs = Product.objects.all()
    if only_selected_ids:
        qs = qs.filter(id__in=only_selected_ids)

    upserts = 0
    for product in qs:
        stock = int(getattr(product, "stock", 0) or 0)

        obj, _ = StorefrontProduct.objects.update_or_create(
            branch_code=branch_code,
            sku=product.sku,
            defaults={
                "product": product,
                "product_name": product.name,
                "price": product.price,
                "available_stock": stock,
            },
        )
        upserts += 1

    StorefrontSyncLog.objects.create(
        direction="billing_to_store",
        ref=f"branch:{branch_code}",
        status="done",
        payload={"count": upserts},
    )
    return upserts


@transaction.atomic
def create_storefront_order(payload: dict) -> StorefrontOrder:
    order = StorefrontOrder.objects.create(
        branch_code=payload.get("branch_code", "default"),
        order_number=payload["order_number"],
        customer_name=payload["customer_name"],
        customer_phone=payload["customer_phone"],
        status=StorefrontOrder.Status.PENDING,
    )

    total = Decimal("0.00")
    for item in payload.get("items", []):
        product = StorefrontProduct.objects.get(id=item["storefront_product_id"])
        qty = int(item.get("quantity", 1))
        line_total = Decimal(product.price) * qty
        StorefrontOrderItem.objects.create(
            order=order,
            product=product,
            quantity=qty,
            unit_price=product.price,
            line_total=line_total,
        )
        total += line_total

    order.total_amount = total
    order.save(update_fields=["total_amount", "updated_at"])

    publish_event_safe(
        event_key="storefront_order_created",
        payload={"storefront_order_id": order.id, "order_number": order.order_number, "total_amount": str(order.total_amount)},
        branch_code=order.branch_code,
        source="ecommerce_engine",
    )
    return order


@transaction.atomic
def mark_payment_paid(order: StorefrontOrder, gateway: str, payment_ref: str):
    order.payment_status = StorefrontOrder.PaymentStatus.PAID
    order.payment_gateway = gateway
    order.payment_ref = payment_ref
    order.status = StorefrontOrder.Status.CONFIRMED
    order.save(update_fields=["payment_status", "payment_gateway", "payment_ref", "status", "updated_at"])

    for item in order.items.select_related("product"):
        product = item.product
        product.available_stock = max(0, product.available_stock - item.quantity)
        product.save(update_fields=["available_stock", "updated_at"])

    publish_event_safe(
        event_key="storefront_order_paid",
        payload={"storefront_order_id": order.id, "order_number": order.order_number, "total_amount": str(order.total_amount)},
        branch_code=order.branch_code,
        source="ecommerce_engine",
    )


def sync_order_back_to_billing(order: StorefrontOrder):
    # Safe adapter: no direct write into legacy billing tables in default mode.
    order.synced_to_billing = True
    order.save(update_fields=["synced_to_billing", "updated_at"])
    StorefrontSyncLog.objects.create(
        direction="store_to_billing",
        ref=order.order_number,
        status="done",
        payload={"order_id": order.id},
    )
