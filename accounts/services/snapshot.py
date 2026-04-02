from decimal import Decimal

from django.core.cache import cache
from django.db.models import DecimalField, F, Sum
from django.db.utils import OperationalError, ProgrammingError
from django.utils.timezone import now

from accounts.models import BusinessSnapshot, LedgerEntry as Transaction, UserProfile as Party

# Commerce module is optional in the real-estate build; guard imports to keep
# dashboard working even when commerce is disabled.
try:
    from commerce.models import Invoice, Order, OrderItem, Payment
except Exception:
    Invoice = Order = OrderItem = Payment = None


def build_business_snapshot(user, date=None, refresh=False):
    date = date or now().date()
    cache_key = f"business_snapshot:{getattr(user, 'pk', user)}:{date.isoformat()}"
    if not refresh:
        cached_snapshot = cache.get(cache_key)
        if cached_snapshot is not None:
            return cached_snapshot
        existing_snapshot = BusinessSnapshot.objects.filter(user=user, date=date).first()
        if existing_snapshot is not None:
            cache.set(cache_key, existing_snapshot, 120)
            return existing_snapshot

    snapshot, _ = BusinessSnapshot.objects.get_or_create(
        user=user,
        date=date,
    )

    decimal_zero = Decimal("0.00")

    # Sales & purchase (skip if commerce is disabled)
    if Order and OrderItem:
        try:
            money_field = DecimalField(max_digits=14, decimal_places=2)

            sales_qs = Order.objects.filter(owner=user, created_at__date=date, order_type="SALE")
            snapshot.sales_orders = sales_qs.count()
            sales_items_total = (
                OrderItem.objects.filter(order__in=sales_qs)
                .aggregate(t=Sum(F("qty") * F("price"), output_field=money_field))["t"]
                or decimal_zero
            )
            sales_discount = sales_qs.aggregate(t=Sum("discount_amount"))["t"] or decimal_zero
            sales_tax = sales_qs.aggregate(t=Sum("tax_amount"))["t"] or decimal_zero
            sales_bill_sundry = sum((o.bill_sundry_total() for o in sales_qs.only("bill_sundry")), decimal_zero)
            snapshot.sales_amount = sales_items_total - sales_discount + sales_tax + sales_bill_sundry

            purchase_qs = Order.objects.filter(owner=user, created_at__date=date, order_type="PURCHASE")
            snapshot.purchase_orders = purchase_qs.count()
            purchase_items_total = (
                OrderItem.objects.filter(order__in=purchase_qs)
                .aggregate(t=Sum(F("qty") * F("price"), output_field=money_field))["t"]
                or decimal_zero
            )
            purchase_discount = purchase_qs.aggregate(t=Sum("discount_amount"))["t"] or decimal_zero
            purchase_tax = purchase_qs.aggregate(t=Sum("tax_amount"))["t"] or decimal_zero
            purchase_bill_sundry = sum((o.bill_sundry_total() for o in purchase_qs.only("bill_sundry")), decimal_zero)
            snapshot.purchase_amount = purchase_items_total - purchase_discount + purchase_tax + purchase_bill_sundry
        except (OperationalError, ProgrammingError):
            snapshot.sales_orders = 0
            snapshot.sales_amount = decimal_zero
            snapshot.purchase_orders = 0
            snapshot.purchase_amount = decimal_zero
    else:
        snapshot.sales_orders = 0
        snapshot.sales_amount = decimal_zero
        snapshot.purchase_orders = 0
        snapshot.purchase_amount = decimal_zero

    # Payments (skip if commerce is disabled)
    if Payment and Order:
        try:
            snapshot.payment_received = (
                Payment.objects.filter(created_at__date=date, invoice__order__owner=user, invoice__order__order_type="SALE")
                .aggregate(t=Sum("amount"))["t"]
                or decimal_zero
            )

            snapshot.payment_given = (
                Payment.objects.filter(created_at__date=date, invoice__order__owner=user, invoice__order__order_type="PURCHASE")
                .aggregate(t=Sum("amount"))["t"]
                or decimal_zero
            )
        except (OperationalError, ProgrammingError):
            snapshot.payment_received = decimal_zero
            snapshot.payment_given = decimal_zero
    else:
        snapshot.payment_received = decimal_zero
        snapshot.payment_given = decimal_zero

    # Receivable / Payable (skip if commerce is disabled)
    if Invoice:
        try:
            snapshot.receivable_amount = (
                Invoice.objects.filter(order__owner=user, order__order_type="SALE", status="unpaid")
                .aggregate(t=Sum("amount"))["t"]
                or decimal_zero
            )

            snapshot.payable_amount = (
                Invoice.objects.filter(order__owner=user, order__order_type="PURCHASE", status="unpaid")
                .aggregate(t=Sum("amount"))["t"]
                or decimal_zero
            )
        except (OperationalError, ProgrammingError):
            snapshot.receivable_amount = decimal_zero
            snapshot.payable_amount = decimal_zero
    else:
        snapshot.receivable_amount = decimal_zero
        snapshot.payable_amount = decimal_zero

    snapshot.net_position = snapshot.receivable_amount - snapshot.payable_amount

    # Counts (KhataApp is enabled in this build)
    snapshot.total_parties = Party.objects.filter(user=user).count()
    snapshot.total_transactions = Transaction.objects.filter(party__user=user, date=date).count()

    snapshot.save()
    cache.set(cache_key, snapshot, 120)
    return snapshot
