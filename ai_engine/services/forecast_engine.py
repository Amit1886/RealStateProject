from __future__ import annotations

import logging
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from ai_engine.models import DemandForecast, ProductDemandForecast
from ai_engine.utils import clamp, date_range, safe_div
from orders.models import Order, OrderItem

logger = logging.getLogger(__name__)

try:
    from prophet import Prophet  # type: ignore
    import pandas as pd  # type: ignore

    PROPHET_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency
    PROPHET_AVAILABLE = False


def _load_sales_history(months: int = 6) -> dict[int, dict]:
    today = timezone.localdate()
    since = today - timedelta(days=max(1, months * 30))

    rows = (
        OrderItem.objects.filter(
            order__order_type=Order.OrderType.ONLINE,
            order__created_at__date__gte=since,
            order__status__in=[Order.Status.DELIVERED, Order.Status.PACKED, Order.Status.OUT_FOR_DELIVERY],
        )
        .values("product_id", "order__created_at__date")
        .annotate(total_qty=Sum("qty"))
        .order_by("product_id", "order__created_at__date")
    )

    data = defaultdict(dict)
    for row in rows:
        product_id = row["product_id"]
        d = row["order__created_at__date"]
        qty = float(row["total_qty"] or 0)
        data[product_id][d] = qty
    return data


def _baseline_forecast(history_by_day: dict, horizon_days: int) -> list[tuple]:
    if not history_by_day:
        return []

    end_date = max(history_by_day.keys())
    start_30 = end_date - timedelta(days=29)
    start_7 = end_date - timedelta(days=6)

    last_30 = [float(history_by_day.get(d, 0.0)) for d in date_range(start_30, end_date)]
    last_7 = [float(history_by_day.get(d, 0.0)) for d in date_range(start_7, end_date)]

    avg30 = safe_div(sum(last_30), len(last_30), 0.0)
    avg7 = safe_div(sum(last_7), len(last_7), avg30)
    daily_trend = avg7 - avg30

    result = []
    for i in range(1, horizon_days + 1):
        target_date = timezone.localdate() + timedelta(days=i)
        projected = max(0.0, avg7 + (daily_trend * 0.15 * i))
        result.append((target_date, round(projected, 2)))
    return result


def _prophet_forecast(history_by_day: dict, horizon_days: int) -> list[tuple]:
    if not PROPHET_AVAILABLE or len(history_by_day) < 15:
        return []
    try:
        rows = [{"ds": d.isoformat(), "y": y} for d, y in sorted(history_by_day.items())]
        df = pd.DataFrame(rows)
        model = Prophet(daily_seasonality=True, weekly_seasonality=True, yearly_seasonality=False)
        model.fit(df)
        future = model.make_future_dataframe(periods=horizon_days, freq="D")
        pred = model.predict(future).tail(horizon_days)

        result = []
        for _, r in pred.iterrows():
            target_date = r["ds"].date()
            qty = float(clamp(float(r["yhat"]), 0.0, 10_000_000.0))
            result.append((target_date, round(qty, 2)))
        return result
    except Exception as exc:  # pragma: no cover - optional path
        logger.warning("Prophet forecast failed; fallback to baseline. error=%s", exc)
        return []


def generate_demand_forecast(days: int = 7, months: int = 6) -> dict:
    """
    Runs forecast asynchronously-safe and stores in new + legacy table.
    Never called from billing save flow.
    """
    try:
        history = _load_sales_history(months=months)
        if not history:
            logger.info("AI forecast: no sales data found for last %s months.", months)
            return {"status": "ok", "message": "No sales data", "products": 0, "rows": 0}

        rows_written = 0
        products_scored = 0

        for product_id, day_map in history.items():
            prediction = _prophet_forecast(day_map, days) or _baseline_forecast(day_map, days)
            if not prediction:
                continue

            products_scored += 1
            with transaction.atomic():
                for predicted_date, predicted_qty in prediction:
                    ProductDemandForecast.objects.update_or_create(
                        product_id=product_id,
                        predicted_date=predicted_date,
                        defaults={"predicted_quantity": float(predicted_qty)},
                    )
                    # Keep legacy table updated for backward compatibility.
                    DemandForecast.objects.update_or_create(
                        product_id=product_id,
                        forecast_date=predicted_date,
                        model_version="ai-v2-baseline",
                        defaults={
                            "predicted_qty": Decimal(str(predicted_qty)),
                            "confidence": Decimal("0.00"),
                        },
                    )
                    rows_written += 1

        logger.info("AI forecast complete. products=%s rows=%s", products_scored, rows_written)
        return {"status": "ok", "products": products_scored, "rows": rows_written}
    except Exception as exc:
        logger.exception("AI forecast failed: %s", exc)
        return {"status": "error", "message": str(exc), "products": 0, "rows": 0}


def latest_forecast_payload(limit: int = 500):
    qs = ProductDemandForecast.objects.select_related("product").order_by("predicted_date", "product_id")[:limit]
    return [
        {
            "product_id": row.product_id,
            "product_name": row.product.name if row.product_id else None,
            "predicted_date": row.predicted_date,
            "predicted_quantity": row.predicted_quantity,
            "created_at": row.created_at,
        }
        for row in qs
    ]
