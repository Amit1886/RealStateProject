from decimal import Decimal
from uuid import uuid4

from django.db import transaction
from django.db.models import Sum

from commission.services.calculator import calculate_margin_commission
from delivery.services.assignment import assign_partner
from products.models import Product
from products.services.inventory import deduct_stock, reserve_stock
from products.services.pricing import get_dynamic_price
from realtime.services.publisher import publish_event
from warehouse.services.routing import nearest_dark_store

from orders.models import Order, OrderItem


def _order_number(prefix="ORD"):
    return f"{prefix}-{uuid4().hex[:10].upper()}"


@transaction.atomic
def place_order(payload: dict, actor=None):
    channel = payload.get("channel", "quick")
    order_type = payload.get("order_type", Order.OrderType.ONLINE)
    latitude = payload.get("latitude")
    longitude = payload.get("longitude")

    warehouse = None
    if latitude is not None and longitude is not None:
        warehouse, dist = nearest_dark_store(float(latitude), float(longitude))
    else:
        warehouse = payload.get("warehouse")
        dist = 0

    order = Order.objects.create(
        order_number=_order_number("POS" if order_type == Order.OrderType.POS else "ORD"),
        order_type=order_type,
        customer_id=payload.get("customer_id"),
        salesman_id=payload.get("salesman_id"),
        warehouse=warehouse,
        walk_in_customer_name=payload.get("walk_in_customer_name", ""),
        is_hold=payload.get("is_hold", False),
        notes=payload.get("notes", ""),
    )

    subtotal = Decimal("0.00")
    cost_total = Decimal("0.00")
    tax_total = Decimal("0.00")
    discount_total = Decimal("0.00")

    for item in payload.get("items", []):
        product = Product.objects.get(id=item["product_id"])
        qty = int(item["qty"])
        unit_price = get_dynamic_price(product, channel=channel, qty=qty)
        unit_cost = Decimal(item.get("unit_cost", "0.00"))
        tax_percent = product.gst_percent
        line_discount = Decimal(str(item.get("discount", "0.00")))
        base = unit_price * qty
        tax = (base - line_discount) * (tax_percent / Decimal("100.00"))
        line_total = base - line_discount + tax
        margin = (unit_price - unit_cost) * qty

        OrderItem.objects.create(
            order=order,
            product=product,
            qty=qty,
            unit_price=unit_price,
            unit_cost=unit_cost,
            tax_percent=tax_percent,
            line_discount=line_discount,
            line_total=line_total,
            margin_total=margin,
        )

        if order.warehouse_id:
            reserve_stock(order.warehouse_id, product.id, qty)
            deduct_stock(order.warehouse_id, product.id, qty)

        subtotal += base
        cost_total += unit_cost * qty
        tax_total += tax
        discount_total += line_discount

    order.subtotal = subtotal
    order.cost_amount = cost_total
    order.tax_amount = tax_total
    order.discount_amount = discount_total
    order.total_amount = subtotal - discount_total + tax_total
    order.margin_amount = order.total_amount - cost_total
    order.save(
        update_fields=[
            "subtotal",
            "cost_amount",
            "tax_amount",
            "discount_amount",
            "total_amount",
            "margin_amount",
            "updated_at",
        ]
    )

    calculate_margin_commission(order)
    if order.order_type != Order.OrderType.POS:
        assign_partner(order, distance_km=dist)
    publish_event("live_orders", "order_created", {"order_number": order.order_number, "status": order.status})
    if order.warehouse_id:
        publish_event("live_inventory", "stock_deducted", {"warehouse_id": order.warehouse_id, "order_number": order.order_number})

    return order


@transaction.atomic
def recalculate_order(order: Order):
    totals = order.items.aggregate(
        subtotal=Sum("line_total"),
        margin=Sum("margin_total"),
        discount=Sum("line_discount"),
    )
    order.total_amount = totals["subtotal"] or Decimal("0.00")
    order.margin_amount = totals["margin"] or Decimal("0.00")
    order.discount_amount = totals["discount"] or Decimal("0.00")
    order.save(update_fields=["total_amount", "margin_amount", "discount_amount", "updated_at"])
    return order
