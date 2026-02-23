from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Tuple

from django.db import transaction
from django.utils.crypto import get_random_string
from django.utils.timezone import now

from addons.ecommerce_engine.models import StorefrontOrder, StorefrontOrderItem, StorefrontPayment, StorefrontProduct


def _generate_order_number() -> str:
    return f"SF-{now().strftime('%Y%m%d')}-{get_random_string(10).upper()}"


def list_published_products(*, branch_code: str = "default", limit: int = 200):
    qs = StorefrontProduct.objects.filter(branch_code=branch_code, is_published=True).order_by("product_name")[:limit]
    return qs


@transaction.atomic
def create_checkout_order(*, branch_code: str, customer_name: str, customer_phone: str, items: List[Dict]) -> Tuple[StorefrontOrder, Dict]:
    if not items:
        raise ValueError("items_required")

    order = StorefrontOrder.objects.create(
        branch_code=branch_code or "default",
        order_number=_generate_order_number(),
        customer_name=customer_name,
        customer_phone=customer_phone,
        status=StorefrontOrder.Status.PENDING,
    )

    total = Decimal("0.00")
    normalized_items = []

    for item in items:
        sku = str(item.get("sku") or "").strip()
        qty = int(item.get("quantity", 1))
        if not sku or qty <= 0:
            raise ValueError("invalid_item")

        product = StorefrontProduct.objects.select_for_update().filter(branch_code=order.branch_code, sku=sku, is_published=True).first()
        if not product:
            raise ValueError("product_not_available")
        if product.available_stock < qty:
            raise ValueError("insufficient_stock")

        line_total = Decimal(product.price) * qty
        StorefrontOrderItem.objects.create(
            order=order,
            product=product,
            quantity=qty,
            unit_price=product.price,
            line_total=line_total,
        )
        total += line_total
        normalized_items.append({"sku": sku, "quantity": qty, "unit_price": str(product.price), "line_total": str(line_total)})

    order.total_amount = total
    order.save(update_fields=["total_amount", "updated_at"])

    return order, {"order_number": order.order_number, "total_amount": str(total), "items": normalized_items}


@transaction.atomic
def record_payment_and_mark_paid(
    *,
    order: StorefrontOrder,
    gateway: str,
    payment_ref: str,
    raw_payload: Dict | None = None,
) -> StorefrontPayment:
    payment = StorefrontPayment.objects.create(
        order=order,
        branch_code=order.branch_code,
        gateway=gateway,
        payment_ref=payment_ref,
        amount=order.total_amount,
        currency=order.currency,
        status=StorefrontPayment.Status.CAPTURED,
        raw_payload=raw_payload or {},
    )
    return payment

