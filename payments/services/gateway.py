from __future__ import annotations

from decimal import Decimal

from payments.models import PaymentOrder


def create_payment_order(*, user, wallet=None, amount=Decimal("0.00"), gateway=None, purpose=None, metadata=None):
    return PaymentOrder.objects.create(
        user=user,
        wallet=wallet,
        amount=amount,
        gateway=gateway or PaymentOrder.Gateway.DUMMY,
        purpose=purpose or PaymentOrder.Purpose.MANUAL,
        metadata=metadata or {},
    )


def build_checkout_context(*, user, invoice=None, amount=None, gateway=None, purpose=None, metadata=None):
    payment_order = create_payment_order(
        user=user,
        wallet=getattr(invoice, "wallet", None),
        amount=amount or getattr(invoice, "total_amount", Decimal("0.00")),
        gateway=gateway or PaymentOrder.Gateway.DUMMY,
        purpose=purpose or PaymentOrder.Purpose.MANUAL,
        metadata=metadata or {},
    )
    return {
        "payment_order": payment_order,
        "invoice": invoice,
        "amount": payment_order.amount,
        "gateway": payment_order.gateway,
        "purpose": payment_order.purpose,
    }
