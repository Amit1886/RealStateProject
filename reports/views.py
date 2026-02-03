from django.shortcuts import render
from django.db.models import Sum, F, Case, When, Value, DecimalField
from django.utils.timezone import now

from khataapp.models import Party, Transaction
from commerce.models import Product, StockEntry


# Create your views here.
def stock_summary(request):
    products = Product.objects.annotate(
        total_in=Sum(
            Case(
                When(stockentry__entry_type='IN', then=F('stockentry__quantity')),
                default=Value(0),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        ),
        total_out=Sum(
            Case(
                When(stockentry__entry_type='OUT', then=F('stockentry__quantity')),
                default=Value(0),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        )
    )

    return render(request, 'reports/stock_summary.html', {
        'products': products
    })


def save_sale(product, qty, party, amount):
    Transaction.objects.create(
        party=party,
        txn_type='credit',
        txn_mode='cash',
        amount=amount,
        date=now().date()
    )

    StockEntry.objects.create(
        product=product,
        quantity=qty,
        entry_type='OUT',
        date=now().date()
    )

def all_transactions(request):
    transactions = Transaction.objects.select_related('party').order_by('-date')
    return render(request, 'reports/all_transactions.html', {
        'transactions': transactions
    })


def cash_book(request):
    transactions = Transaction.objects.filter(txn_mode='cash')

    total_in = transactions.filter(txn_type='credit').aggregate(
        total=Sum('amount')
    )['total'] or 0

    total_out = transactions.filter(txn_type='debit').aggregate(
        total=Sum('amount')
    )['total'] or 0

    return render(request, 'reports/cash_book.html', {
        'transactions': transactions,
        'total_in': total_in,
        'total_out': total_out,
        'balance': total_in - total_out
    })


def voucher_report(request):
    vouchers = Transaction.objects.all().order_by('-date')
    return render(request, 'reports/voucher_report.html', {
        'vouchers': vouchers
    })


def sales_report(request):
    sales = Transaction.objects.filter(txn_type='credit')

    total_sales = sales.aggregate(
        total=Sum('amount')
    )['total'] or 0

    return render(request, 'reports/sales_report.html', {
        'sales': sales,
        'total_sales': total_sales
    })


def purchase_report(request):
    purchases = Transaction.objects.filter(txn_type='debit')

    total_purchase = purchases.aggregate(
        total=Sum('amount')
    )['total'] or 0

    return render(request, 'reports/purchase_report.html', {
        'purchases': purchases,
        'total_purchase': total_purchase
    })


def low_stock(request):
    products = Product.objects.filter(
        stock__lte=F('min_stock')
    )

    return render(request, 'reports/low_stock.html', {
        'products': products
    })


def party_ledger(request):
    party_id = request.GET.get('party')

    parties = Party.objects.all()
    transactions = Transaction.objects.none()

    if party_id:
        transactions = Transaction.objects.filter(
            party_id=party_id
        ).order_by('date')

    return render(request, 'reports/party_ledger.html', {
        'parties': parties,
        'transactions': transactions,
        'selected_party': party_id
    })


def outstanding(request):
    parties = Party.objects.annotate(
        balance=Sum('transactions__amount')
    )

    return render(request, 'reports/outstanding.html', {
        'parties': parties
    })


def profit_loss(request):
    income = Transaction.objects.filter(
        txn_type='credit'
    ).aggregate(total=Sum('amount'))['total'] or 0

    expense = Transaction.objects.filter(
        txn_type='debit'
    ).aggregate(total=Sum('amount'))['total'] or 0

    return render(request, 'reports/profit_loss.html', {
        'income': income,
        'expense': expense,
        'profit': income - expense
    })


def day_book(request):
    today = now().date()
    transactions = Transaction.objects.filter(date=today)

    return render(request, 'reports/day_book.html', {
        'transactions': transactions,
        'date': today
    })
