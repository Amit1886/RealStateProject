from decimal import Decimal
from django.db.models import Sum
from django.utils.timezone import now

from accounts.models import BusinessSnapshot
from commerce.models import Order, Payment
from khataapp.models import Transaction, Party


def build_business_snapshot(user, date=None):
    date = date or now().date()

    snapshot, _ = BusinessSnapshot.objects.get_or_create(
        user=user,
        date=date
    )

    # ====
    # 🔹 SALES
    # ====
    sales_qs = Order.objects.filter(
        owner=user,
        created_at__date=date
    )

    snapshot.sales_orders = sales_qs.count()
    snapshot.sales_amount = sum(
        (o.total_amount() for o in sales_qs),
        Decimal("0.00")
    )

    # ====
    # 🔹 PURCHASE
    # ====
    purchase_qs = Order.objects.filter(
        owner=user,
        created_at__date=date
    )

    snapshot.purchase_orders = purchase_qs.count()
    snapshot.purchase_amount = sum(
        (o.total_amount() for o in purchase_qs),
        Decimal("0.00")
    )

    # ====
    # 🔹 PAYMENTS
    # ====
    snapshot.payment_received = Payment.objects.filter(
        created_at__date=date,
        amount__gt=0
    ).aggregate(
        t=Sum("amount")
    )["t"] or Decimal("0.00")

    snapshot.payment_given = Payment.objects.filter(
        created_at__date=date,
        amount__lt=0
    ).aggregate(
        t=Sum("amount")
    )["t"] or Decimal("0.00")

    # ====
    # 🔹 RECEIVABLE (Customer se lena)
    # ====
    snapshot.receivable_amount = Transaction.objects.filter(
        txn_type__in=["SALE", "RECEIVABLE"]
    ).aggregate(
        t=Sum("amount")
    )["t"] or Decimal("0.00")

    # ====
    # 🔹 PAYABLE (Supplier ko dena)
    # ====
    snapshot.payable_amount = Transaction.objects.filter(
        txn_type__in=["PURCHASE", "PAYABLE"]
    ).aggregate(
        t=Sum("amount")
    )["t"] or Decimal("0.00")

    snapshot.net_position = (
        snapshot.receivable_amount - snapshot.payable_amount
    )

    # ====
    # 🔹 COUNTS
    # ====
    snapshot.total_parties = Party.objects.count()

    snapshot.total_transactions = Transaction.objects.filter(
        date=date
    ).count()

    snapshot.save()
    return snapshot
