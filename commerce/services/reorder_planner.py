from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
import math

from django.db.models import (
    Avg,
    Case,
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    Max,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce
from django.utils import timezone

from commerce.models import Product, StockEntry, OrderItem, CommerceAISettings
from khataapp.models import Party, StockLedger


DECIMAL_ZERO = Decimal("0.00")

def _get_ai_settings():
    settings_obj = CommerceAISettings.objects.first()
    if not settings_obj:
        settings_obj = CommerceAISettings.objects.create()
    return settings_obj


def _to_decimal(value, default=DECIMAL_ZERO) -> Decimal:
    if value is None:
        return default
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:
        return default


def _safe_int(value, default=0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _classify_demand(avg_daily_sales: Decimal, settings_obj) -> str:
    if avg_daily_sales <= 0:
        return "dead"
    if avg_daily_sales >= settings_obj.fast_daily_sales:
        return "fast"
    if avg_daily_sales >= settings_obj.medium_daily_sales:
        return "medium"
    if avg_daily_sales >= settings_obj.slow_daily_sales:
        return "slow"
    return "slow"


def _avg(values):
    if not values:
        return None
    return sum(values) / len(values)


def _compute_lead_times(user=None):
    lead_times_by_supplier = defaultdict(list)
    ledger_qs = StockLedger.objects.filter(
        ledger_type="in",
        order__order_type__iexact="purchase",
    )
    if user:
        ledger_qs = ledger_qs.filter(order__owner=user)

    rows = ledger_qs.values("order__party_id", "created_at", "order__created_at")
    for row in rows:
        if not row.get("order__party_id") or not row.get("created_at") or not row.get("order__created_at"):
            continue
        delta = row["created_at"].date() - row["order__created_at"].date()
        days = max(delta.days, 0)
        lead_times_by_supplier[row["order__party_id"]].append(days)

    lead_time_days = {}
    for supplier_id, values in lead_times_by_supplier.items():
        lead_time_days[supplier_id] = int(round(_avg(values))) if values else None

    return lead_time_days


def build_reorder_plan(
    user=None,
    budget=Decimal("50000"),
    target_stock_days=30,
    safety_factor=None,
    as_of=None,
):
    as_of = as_of or timezone.now().date()
    settings_obj = _get_ai_settings()
    budget = _to_decimal(budget, settings_obj.default_budget)
    target_stock_days = _safe_int(target_stock_days, settings_obj.default_target_days)
    if safety_factor is None:
        safety_factor = settings_obj.safety_factor
    safety_factor = _to_decimal(safety_factor, settings_obj.safety_factor)

    product_qs = Product.objects.all()
    if user:
        product_qs = product_qs.filter(owner=user)

    # Stock ledger entries (net stock)
    stock_qs = StockEntry.objects.all()
    if user:
        stock_qs = stock_qs.filter(product__owner=user)

    stock_rows = stock_qs.values("product_id").annotate(
        total_in=Coalesce(
            Sum(
                Case(
                    When(entry_type="IN", then=F("quantity")),
                    default=Value(0),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )
            ),
            Value(0, output_field=DecimalField(max_digits=12, decimal_places=2)),
        ),
        total_out=Coalesce(
            Sum(
                Case(
                    When(entry_type="OUT", then=F("quantity")),
                    default=Value(0),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )
            ),
            Value(0, output_field=DecimalField(max_digits=12, decimal_places=2)),
        ),
        entries=Coalesce(Count("id"), Value(0)),
    )
    stock_map = {
        row["product_id"]: {
            "total_in": _to_decimal(row["total_in"]),
            "total_out": _to_decimal(row["total_out"]),
            "entries": _safe_int(row["entries"]),
        }
        for row in stock_rows
    }

    # Sales history aggregates
    sales_items = OrderItem.objects.filter(order__order_type__iexact="sale")
    if user:
        sales_items = sales_items.filter(order__owner=user)

    d30 = as_of - timedelta(days=30)
    d60 = as_of - timedelta(days=60)
    d90 = as_of - timedelta(days=90)
    d7 = as_of - timedelta(days=7)
    d28 = as_of - timedelta(days=28)

    revenue_expr = ExpressionWrapper(
        F("qty") * F("price"),
        output_field=DecimalField(max_digits=14, decimal_places=2),
    )

    sales_rows = sales_items.values("product_id").annotate(
        qty_30=Coalesce(
            Sum(
                Case(
                    When(order__created_at__date__gte=d30, then=F("qty")),
                    default=Value(0),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )
            ),
            Value(0, output_field=DecimalField(max_digits=12, decimal_places=2)),
        ),
        qty_60=Coalesce(
            Sum(
                Case(
                    When(order__created_at__date__gte=d60, then=F("qty")),
                    default=Value(0),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )
            ),
            Value(0, output_field=DecimalField(max_digits=12, decimal_places=2)),
        ),
        qty_90=Coalesce(
            Sum(
                Case(
                    When(order__created_at__date__gte=d90, then=F("qty")),
                    default=Value(0),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )
            ),
            Value(0, output_field=DecimalField(max_digits=12, decimal_places=2)),
        ),
        qty_7=Coalesce(
            Sum(
                Case(
                    When(order__created_at__date__gte=d7, then=F("qty")),
                    default=Value(0),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )
            ),
            Value(0, output_field=DecimalField(max_digits=12, decimal_places=2)),
        ),
        qty_28=Coalesce(
            Sum(
                Case(
                    When(order__created_at__date__gte=d28, then=F("qty")),
                    default=Value(0),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )
            ),
            Value(0, output_field=DecimalField(max_digits=12, decimal_places=2)),
        ),
        revenue_90=Coalesce(
            Sum(
                Case(
                    When(order__created_at__date__gte=d90, then=revenue_expr),
                    default=Value(0),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            ),
            Value(0, output_field=DecimalField(max_digits=14, decimal_places=2)),
        ),
    )
    sales_map = {
        row["product_id"]: {
            "qty_30": _to_decimal(row["qty_30"]),
            "qty_60": _to_decimal(row["qty_60"]),
            "qty_90": _to_decimal(row["qty_90"]),
            "qty_7": _to_decimal(row["qty_7"]),
            "qty_28": _to_decimal(row["qty_28"]),
            "revenue_90": _to_decimal(row["revenue_90"]),
        }
        for row in sales_rows
    }

    # Purchase pricing and supplier mapping
    purchase_items = OrderItem.objects.filter(order__order_type__iexact="purchase")
    if user:
        purchase_items = purchase_items.filter(order__owner=user)

    purchase_rows = purchase_items.values("product_id", "order__party_id").annotate(
        avg_unit_cost=Avg("price"),
        last_purchase=Max("order__created_at"),
    )

    supplier_options = defaultdict(list)
    for row in purchase_rows:
        supplier_id = row.get("order__party_id")
        if not supplier_id:
            continue
        supplier_options[row["product_id"]].append(
            {
                "supplier_id": supplier_id,
                "avg_unit_cost": _to_decimal(row.get("avg_unit_cost")),
                "last_purchase": row.get("last_purchase"),
            }
        )

    suppliers = Party.objects.filter(party_type="supplier")
    if user:
        suppliers = suppliers.filter(owner=user)
    supplier_name_map = {s.id: s.name for s in suppliers}
    supplier_credit_period = {s.id: s.credit_period or 30 for s in suppliers}

    lead_time_by_supplier = _compute_lead_times(user=user)

    items = []
    skipped = []

    max_velocity = Decimal("0.01")
    max_revenue = Decimal("0.01")
    max_margin = Decimal("0.01")

    # First pass: compute demand signals and base reorder quantities
    for product in product_qs:
        product_sales = sales_map.get(product.id, {})
        qty_30 = product_sales.get("qty_30", DECIMAL_ZERO)
        qty_90 = product_sales.get("qty_90", DECIMAL_ZERO)
        qty_7 = product_sales.get("qty_7", DECIMAL_ZERO)
        qty_28 = product_sales.get("qty_28", DECIMAL_ZERO)
        revenue_90 = product_sales.get("revenue_90", DECIMAL_ZERO)

        avg_daily_30 = qty_30 / Decimal("30")
        avg_daily_90 = qty_90 / Decimal("90") if qty_90 > 0 else DECIMAL_ZERO

        demand_class = _classify_demand(avg_daily_30, settings_obj)

        stock_info = stock_map.get(product.id)
        if stock_info and stock_info["entries"] > 0:
            current_available = stock_info["total_in"] - stock_info["total_out"]
        else:
            current_available = _to_decimal(product.stock)

        supplier_choice = None
        supplier_id = None
        unit_cost = None
        lead_time_days = None

        options = supplier_options.get(product.id, [])
        if options:
            # Choose best supplier: lowest cost, then fastest lead time
            def sort_key(opt):
                lead = lead_time_by_supplier.get(opt["supplier_id"])
                lead = lead if lead is not None else 9999
                return (opt["avg_unit_cost"] or Decimal("999999"), lead)

            options_sorted = sorted(options, key=sort_key)
            best = options_sorted[0]
            supplier_id = best["supplier_id"]
            supplier_choice = supplier_name_map.get(supplier_id, "Supplier")
            unit_cost = best["avg_unit_cost"]
            lead_time_days = lead_time_by_supplier.get(supplier_id)

        if unit_cost is None or unit_cost <= 0:
            unit_cost = _to_decimal(product.price) * Decimal("0.7") if product.price else Decimal("1.0")

        if lead_time_days is None:
            fallback = supplier_credit_period.get(supplier_id, 30) if supplier_id else 30
            lead_time_days = max(3, int(round(fallback / 4)))

        safety_stock = avg_daily_30 * Decimal(str(lead_time_days)) * safety_factor
        reorder_qty = (avg_daily_30 * Decimal(str(target_stock_days))) + safety_stock - current_available
        reorder_qty = max(Decimal("0"), reorder_qty)

        # Seasonal spike and anomaly detection
        seasonal_spike = avg_daily_90 > 0 and avg_daily_30 > (avg_daily_90 * Decimal("1.4"))
        anomaly_spike = False
        anomaly_drop = False

        prev_21_qty = max(qty_28 - qty_7, DECIMAL_ZERO)
        avg_daily_7 = qty_7 / Decimal("7") if qty_7 > 0 else DECIMAL_ZERO
        avg_daily_prev = prev_21_qty / Decimal("21") if prev_21_qty > 0 else DECIMAL_ZERO

        if avg_daily_prev > 0:
            ratio = avg_daily_7 / avg_daily_prev
            anomaly_spike = ratio >= Decimal("1.8")
            anomaly_drop = ratio <= Decimal("0.5")

        if seasonal_spike:
            reorder_qty *= Decimal("1.2")

        reorder_qty_int = int(math.ceil(reorder_qty)) if reorder_qty > 0 else 0

        stock_days = None
        if avg_daily_30 > 0:
            stock_days = float(current_available / avg_daily_30)

        stock_out_risk_date = None
        if avg_daily_30 > 0:
            days_to_stockout = int(math.floor(current_available / avg_daily_30))
            stock_out_risk_date = as_of + timedelta(days=max(days_to_stockout, 0))

        margin_per_unit = _to_decimal(product.price) - unit_cost
        margin_pct = (margin_per_unit / _to_decimal(product.price)) if product.price else DECIMAL_ZERO

        max_velocity = max(max_velocity, avg_daily_30)
        max_revenue = max(max_revenue, revenue_90)
        max_margin = max(max_margin, margin_pct)

        items.append(
            {
                "product_id": product.id,
                "name": product.name,
                "sku": product.sku,
                "current_available": float(current_available),
                "avg_daily_sales": float(avg_daily_30),
                "avg_daily_sales_90": float(avg_daily_90),
                "demand_class": demand_class,
                "reorder_qty": reorder_qty_int,
                "unit_cost": float(unit_cost),
                "lead_time_days": lead_time_days,
                "supplier_id": supplier_id,
                "supplier_name": supplier_choice,
                "stock_days": stock_days,
                "stock_out_risk_date": stock_out_risk_date.isoformat() if stock_out_risk_date else None,
                "seasonal_spike": seasonal_spike,
                "anomaly_spike": anomaly_spike,
                "anomaly_drop": anomaly_drop,
                "revenue_90": float(revenue_90),
                "margin_pct": float(margin_pct) if margin_pct is not None else 0.0,
            }
        )

    # Scoring and ranking
    for item in items:
        velocity_score = Decimal(str(item["avg_daily_sales"])) / max_velocity
        revenue_score = Decimal(str(item["revenue_90"])) / max_revenue
        margin_score = Decimal(str(item["margin_pct"])) / max_margin if max_margin else DECIMAL_ZERO
        score = (velocity_score * Decimal("0.5")) + (revenue_score * Decimal("0.3")) + (margin_score * Decimal("0.2"))
        item["score"] = float(score)

    items.sort(
        key=lambda x: (
            {"fast": 0, "medium": 1, "slow": 2, "dead": 3}.get(x["demand_class"], 4),
            -x["score"],
        )
    )

    # Budget optimization with coverage-first strategy
    allocated = []
    budget_remaining = budget

    def _target_multiplier(demand_class):
        if demand_class == "fast":
            return Decimal("1.0")
        if demand_class == "medium":
            return Decimal("0.6")
        if demand_class == "slow":
            return Decimal("0.3")
        return Decimal("0.0")

    # Phase 1: ensure SKU coverage for fast/medium
    for item in items:
        if item["reorder_qty"] <= 0:
            continue
        if item["demand_class"] not in ("fast", "medium"):
            continue
        unit_cost = _to_decimal(item["unit_cost"])
        if budget_remaining < unit_cost or unit_cost <= 0:
            continue
        item["allocated_qty"] = 1
        item["total_cost"] = float(unit_cost)
        budget_remaining -= unit_cost
        allocated.append(item)

    # Phase 2: top-up to target
    for item in items:
        if item["reorder_qty"] <= 0:
            continue

        unit_cost = _to_decimal(item["unit_cost"])
        if unit_cost <= 0:
            skipped.append(
                {
                    "product_id": item["product_id"],
                    "name": item["name"],
                    "reason": "Invalid unit cost",
                }
            )
            continue

        target_qty = int(math.ceil(item["reorder_qty"] * float(_target_multiplier(item["demand_class"]))))
        if target_qty <= 0:
            skipped.append(
                {
                    "product_id": item["product_id"],
                    "name": item["name"],
                    "reason": "Low priority or dead stock",
                }
            )
            continue

        already = item.get("allocated_qty", 0)
        remaining_qty = max(target_qty - already, 0)
        if remaining_qty == 0:
            continue

        affordable_qty = int(budget_remaining // unit_cost) if unit_cost > 0 else 0
        if affordable_qty <= 0:
            skipped.append(
                {
                    "product_id": item["product_id"],
                    "name": item["name"],
                    "reason": "Budget limit reached",
                }
            )
            continue

        final_qty = min(remaining_qty, affordable_qty)
        item["allocated_qty"] = already + final_qty
        item["total_cost"] = float(unit_cost * final_qty + unit_cost * already)
        budget_remaining -= unit_cost * final_qty

        if final_qty < remaining_qty:
            item["budget_note"] = "Partial quantity due to budget"

        allocated.append(item)

    # Deduplicate allocated list by product_id
    allocated_map = {}
    for item in allocated:
        allocated_map[item["product_id"]] = item
    allocated = list(allocated_map.values())

    supplier_groups = {}
    total_purchase_cost = Decimal("0.00")

    for item in allocated:
        qty = item.get("allocated_qty", 0)
        if qty <= 0:
            continue
        unit_cost = _to_decimal(item["unit_cost"])
        total_cost = unit_cost * qty
        total_purchase_cost += total_cost

        reason_bits = []
        if item["demand_class"] in ("fast", "medium"):
            reason_bits.append("high sales velocity")
        if item["seasonal_spike"]:
            reason_bits.append("seasonal spike detected")
        if item["anomaly_spike"]:
            reason_bits.append("anomaly demand jump")
        if item["stock_days"] is not None and item["stock_days"] < target_stock_days:
            reason_bits.append("low stock coverage")
        if item["lead_time_days"] and item["lead_time_days"] >= 7:
            reason_bits.append("long supplier lead time")

        item["why_reorder"] = ", ".join(reason_bits) or "stock coverage optimization"

        supplier_key = item.get("supplier_id") or 0
        if supplier_key not in supplier_groups:
            supplier_groups[supplier_key] = {
                "supplier_id": item.get("supplier_id"),
                "supplier_name": item.get("supplier_name") or "Unassigned Supplier",
                "items": [],
                "total_cost": 0.0,
            }

        supplier_groups[supplier_key]["items"].append(
            {
                "product": item["name"],
                "sku": item["sku"],
                "qty": qty,
                "unit_cost": float(unit_cost),
                "total_cost": float(total_cost),
                "stock_days": item["stock_days"],
                "lead_time_days": item["lead_time_days"],
                "why_reorder": item["why_reorder"],
            }
        )
        supplier_groups[supplier_key]["total_cost"] += float(total_cost)

    # Summary metrics
    allocated_count = sum(1 for item in allocated if item.get("allocated_qty", 0) > 0)
    expected_stock_days = []
    for item in allocated:
        if item["avg_daily_sales"] > 0:
            new_stock = Decimal(str(item["current_available"])) + Decimal(str(item.get("allocated_qty", 0)))
            expected_stock_days.append(float(new_stock / Decimal(str(item["avg_daily_sales"]))))

    avg_stock_stability = round(sum(expected_stock_days) / len(expected_stock_days), 1) if expected_stock_days else 0

    top_fast = sorted(
        [i for i in items if i["demand_class"] == "fast"],
        key=lambda x: -x["avg_daily_sales"],
    )[:5]

    risk_items = sorted(
        [i for i in items if i["stock_out_risk_date"]],
        key=lambda x: x["stock_out_risk_date"],
    )[:5]

    summary = {
        "generated_at": timezone.now().isoformat(),
        "budget": float(budget),
        "budget_used": float(total_purchase_cost),
        "budget_remaining": float(max(budget - total_purchase_cost, Decimal("0"))),
        "total_items_reordered": allocated_count,
        "items_skipped": skipped[:20],
        "expected_stock_stability_days": avg_stock_stability,
        "learning_confidence": min(100, int(len(items) * 3)),
    }

    return {
        "summary": summary,
        "items": allocated,
        "supplier_groups": supplier_groups,
        "top_fast_moving": top_fast,
        "risk_items": risk_items,
    }


def build_reorder_summary(user=None, budget=Decimal("50000"), target_stock_days=30):
    plan = build_reorder_plan(
        user=user,
        budget=budget,
        target_stock_days=target_stock_days,
    )

    summary = plan["summary"]
    return {
        "generated_at": summary["generated_at"],
        "budget": summary["budget"],
        "budget_used": summary["budget_used"],
        "budget_remaining": summary["budget_remaining"],
        "total_items_reordered": summary["total_items_reordered"],
        "expected_stock_stability_days": summary["expected_stock_stability_days"],
        "learning_confidence": summary["learning_confidence"],
        "fast_moving": [
            {
                "name": item["name"],
                "sku": item["sku"],
                "velocity": item["avg_daily_sales"],
            }
            for item in plan["top_fast_moving"]
        ],
        "risk_items": [
            {
                "name": item["name"],
                "sku": item["sku"],
                "stock_out_risk_date": item["stock_out_risk_date"],
            }
            for item in plan["risk_items"]
        ],
    }
