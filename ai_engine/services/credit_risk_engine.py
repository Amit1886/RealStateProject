from __future__ import annotations

import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone

from ai_engine.models import CustomerRiskScore
from ai_engine.utils import clamp, safe_div
from orders.models import Order
from payments.models import PaymentTransaction
from users.models import UserProfileExt, UserRole

logger = logging.getLogger(__name__)
User = get_user_model()


def _risk_level(score: int) -> str:
    if score >= 67:
        return CustomerRiskScore.RiskLevel.HIGH
    if score >= 34:
        return CustomerRiskScore.RiskLevel.MEDIUM
    return CustomerRiskScore.RiskLevel.LOW


def _customer_queryset():
    role_ids = UserProfileExt.objects.filter(
        role__in=[UserRole.B2B_CUSTOMER, UserRole.B2C_CUSTOMER]
    ).values_list("user_id", flat=True)
    return User.objects.filter(id__in=role_ids)


def calculate_credit_risk_scores() -> dict:
    """
    Calculates customer risk score in background only.
    Does not affect billing flow on failure.
    """
    try:
        customers = list(_customer_queryset())
        if not customers:
            logger.info("AI credit-risk: no customer users found.")
            return {"status": "ok", "customers": 0}

        now = timezone.now()
        overdue_cutoff = now - timedelta(days=30)
        processed = 0

        for customer in customers:
            customer_orders = Order.objects.filter(customer=customer)
            totals = customer_orders.aggregate(
                order_total=Sum("total_amount"),
                order_count=Count("id"),
            )
            total_order_amount = float(totals["order_total"] or 0.0)

            payment_totals = PaymentTransaction.objects.filter(
                Q(user=customer) | Q(order__customer=customer),
                status=PaymentTransaction.Status.SUCCESS,
            ).aggregate(total_paid=Sum("amount"))
            total_paid = float(payment_totals["total_paid"] or 0.0)

            overdue_count = customer_orders.filter(
                created_at__lt=overdue_cutoff
            ).exclude(
                payments__status=PaymentTransaction.Status.SUCCESS
            ).distinct().count()

            failed_payment_count = PaymentTransaction.objects.filter(
                Q(user=customer) | Q(order__customer=customer),
                status=PaymentTransaction.Status.FAILED,
            ).count()

            # Collection speed proxy (python loop for DB portability).
            paid_orders = (
                customer_orders.filter(payments__status=PaymentTransaction.Status.SUCCESS)
                .distinct()
                .prefetch_related("payments")
            )
            delay_values = []
            for order in paid_orders:
                first_payment = (
                    order.payments.filter(status=PaymentTransaction.Status.SUCCESS).order_by("created_at").first()
                )
                if first_payment:
                    delay = (first_payment.created_at - order.created_at).total_seconds() / 86400
                    delay_values.append(max(0.0, delay))
            avg_delay = sum(delay_values) / len(delay_values) if delay_values else 0.0

            paid_ratio = safe_div(total_paid, total_order_amount, default=1.0 if total_order_amount == 0 else 0.0)

            coverage_penalty = (1.0 - clamp(paid_ratio, 0.0, 1.0)) * 45.0
            overdue_penalty = min(35.0, overdue_count * 8.0)
            failure_penalty = min(15.0, failed_payment_count * 3.0)
            delay_penalty = min(20.0, avg_delay * 1.5)

            risk_score = int(round(clamp(coverage_penalty + overdue_penalty + failure_penalty + delay_penalty, 0, 100)))
            risk_level = _risk_level(risk_score)

            with transaction.atomic():
                CustomerRiskScore.objects.update_or_create(
                    customer=customer,
                    defaults={
                        "risk_score": risk_score,
                        "risk_level": risk_level,
                    },
                )
            processed += 1

        logger.info("AI credit-risk complete. customers=%s", processed)
        return {"status": "ok", "customers": processed}
    except Exception as exc:
        logger.exception("AI credit-risk failed: %s", exc)
        return {"status": "error", "message": str(exc), "customers": 0}


def latest_credit_risk_payload(limit: int = 500):
    qs = CustomerRiskScore.objects.select_related("customer").order_by("-last_calculated", "-risk_score")[:limit]
    return [
        {
            "customer_id": row.customer_id,
            "customer_name": row.customer.get_full_name() or row.customer.email,
            "risk_score": row.risk_score,
            "risk_level": row.risk_level,
            "last_calculated": row.last_calculated,
        }
        for row in qs
    ]
