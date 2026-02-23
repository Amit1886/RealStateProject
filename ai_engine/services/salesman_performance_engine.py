from __future__ import annotations

import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q, Sum

from ai_engine.models import SalesmanScore
from ai_engine.utils import clamp, safe_div
from orders.models import Order
from payments.models import PaymentTransaction
from users.models import UserProfileExt, UserRole

logger = logging.getLogger(__name__)
User = get_user_model()


def _salesman_queryset():
    role_ids = UserProfileExt.objects.filter(role=UserRole.SALESMAN).values_list("user_id", flat=True)
    order_ids = Order.objects.filter(salesman__isnull=False).values_list("salesman_id", flat=True)
    user_ids = set(list(role_ids) + list(order_ids))
    return User.objects.filter(id__in=user_ids)


def _collection_speed_component(avg_days: float) -> int:
    if avg_days <= 1:
        return 25
    if avg_days <= 3:
        return 20
    if avg_days <= 7:
        return 14
    if avg_days <= 14:
        return 8
    return 3


def calculate_salesman_scores() -> dict:
    """
    Salesman performance scoring in async-safe engine.
    Never runs inside billing transaction hooks.
    """
    try:
        salesmen = list(_salesman_queryset())
        if not salesmen:
            logger.info("AI salesman-score: no salesman users found.")
            return {"status": "ok", "salesmen": 0}

        processed = 0
        for salesman in salesmen:
            qs = Order.objects.filter(salesman=salesman)
            order_count = qs.count()
            if order_count == 0:
                with transaction.atomic():
                    SalesmanScore.objects.update_or_create(
                        salesman=salesman,
                        defaults={"performance_score": 0, "risk_flag": True},
                    )
                processed += 1
                continue

            sales_amount = float(
                qs.exclude(status=Order.Status.CANCELLED)
                .aggregate(v=Sum("total_amount"))["v"]
                or 0.0
            )
            returns_count = qs.filter(Q(is_return=True) | Q(status=Order.Status.CANCELLED)).count()
            return_rate = safe_div(returns_count, order_count, 0.0)

            paid_orders = (
                qs.filter(payments__status=PaymentTransaction.Status.SUCCESS)
                .distinct()
                .prefetch_related("payments")
            )
            delay_values = []
            for order in paid_orders:
                first_payment = (
                    order.payments.filter(status=PaymentTransaction.Status.SUCCESS).order_by("created_at").first()
                )
                if first_payment:
                    days = (first_payment.created_at - order.created_at).total_seconds() / 86400
                    delay_values.append(max(0.0, days))
            avg_collection_days = sum(delay_values) / len(delay_values) if delay_values else 0.0

            sales_component = min(55, int(sales_amount / 2000.0))
            quality_component = max(0, 20 - int(return_rate * 40))
            collection_component = _collection_speed_component(avg_collection_days)
            performance_score = int(round(clamp(sales_component + quality_component + collection_component, 0, 100)))
            risk_flag = performance_score < 40 or return_rate >= 0.35

            with transaction.atomic():
                SalesmanScore.objects.update_or_create(
                    salesman=salesman,
                    defaults={
                        "performance_score": performance_score,
                        "risk_flag": risk_flag,
                    },
                )
            processed += 1

        logger.info("AI salesman-score complete. salesmen=%s", processed)
        return {"status": "ok", "salesmen": processed}
    except Exception as exc:
        logger.exception("AI salesman-score failed: %s", exc)
        return {"status": "error", "message": str(exc), "salesmen": 0}


def latest_salesman_payload(limit: int = 500):
    qs = SalesmanScore.objects.select_related("salesman").order_by("-calculated_at", "-performance_score")[:limit]
    return [
        {
            "salesman_id": row.salesman_id,
            "salesman_name": row.salesman.get_full_name() or row.salesman.email,
            "performance_score": row.performance_score,
            "risk_flag": row.risk_flag,
            "calculated_at": row.calculated_at,
        }
        for row in qs
    ]
