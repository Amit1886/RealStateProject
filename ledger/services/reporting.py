from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Optional

from django.db.models import DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce

from ledger.models import LedgerAccount, LedgerEntry, LedgerTransaction, StockLedger


DECIMAL_ZERO = Decimal("0.00")


def _d(value) -> Decimal:
    if value is None:
        return DECIMAL_ZERO
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:
        return DECIMAL_ZERO


def trial_balance(*, owner, date_from: date, date_to: date):
    """
    Trial Balance from GL (LedgerEntry only).

    Conventions:
    - Net balance = Debit - Credit
    - Opening = sum before `date_from`
    - Period = sums between [date_from, date_to]
    - Closing = Opening + (PeriodDR - PeriodCR)
    """
    money_field = DecimalField(max_digits=14, decimal_places=2)

    base = LedgerEntry.objects.filter(transaction__owner=owner, transaction__date__lte=date_to)

    rows = (
        base.values("account_id", "account__code", "account__name", "account__account_type")
        .annotate(
            opening_debit=Coalesce(Sum("debit", filter=Q(transaction__date__lt=date_from)), Value(0, output_field=money_field)),
            opening_credit=Coalesce(Sum("credit", filter=Q(transaction__date__lt=date_from)), Value(0, output_field=money_field)),
            period_debit=Coalesce(Sum("debit", filter=Q(transaction__date__gte=date_from, transaction__date__lte=date_to)), Value(0, output_field=money_field)),
            period_credit=Coalesce(Sum("credit", filter=Q(transaction__date__gte=date_from, transaction__date__lte=date_to)), Value(0, output_field=money_field)),
        )
        .order_by("account__code")
    )

    results = []
    totals = {
        "opening_debit": DECIMAL_ZERO,
        "opening_credit": DECIMAL_ZERO,
        "period_debit": DECIMAL_ZERO,
        "period_credit": DECIMAL_ZERO,
        "closing_debit": DECIMAL_ZERO,
        "closing_credit": DECIMAL_ZERO,
    }

    for r in rows:
        opening_net = _d(r["opening_debit"]) - _d(r["opening_credit"])
        closing_net = opening_net + (_d(r["period_debit"]) - _d(r["period_credit"]))

        opening_debit = opening_net if opening_net > 0 else DECIMAL_ZERO
        opening_credit = (-opening_net) if opening_net < 0 else DECIMAL_ZERO
        closing_debit = closing_net if closing_net > 0 else DECIMAL_ZERO
        closing_credit = (-closing_net) if closing_net < 0 else DECIMAL_ZERO

        row = {
            "account_id": r["account_id"],
            "code": r["account__code"],
            "name": r["account__name"],
            "account_type": r["account__account_type"],
            "opening_debit": opening_debit,
            "opening_credit": opening_credit,
            "debit": _d(r["period_debit"]),
            "credit": _d(r["period_credit"]),
            "closing_debit": closing_debit,
            "closing_credit": closing_credit,
        }
        results.append(row)

        totals["opening_debit"] += opening_debit
        totals["opening_credit"] += opening_credit
        totals["period_debit"] += row["debit"]
        totals["period_credit"] += row["credit"]
        totals["closing_debit"] += closing_debit
        totals["closing_credit"] += closing_credit

    return {"rows": results, "totals": totals, "date_from": date_from, "date_to": date_to}


def profit_and_loss(*, owner, date_from: date, date_to: date):
    money_field = DecimalField(max_digits=14, decimal_places=2)

    base = LedgerEntry.objects.filter(transaction__owner=owner, transaction__date__gte=date_from, transaction__date__lte=date_to)

    by_account = (
        base.values("account_id", "account__code", "account__name", "account__account_type")
        .filter(account__account_type__in=[LedgerAccount.AccountType.INCOME, LedgerAccount.AccountType.EXPENSE])
        .annotate(
            debit=Coalesce(Sum("debit"), Value(0, output_field=money_field)),
            credit=Coalesce(Sum("credit"), Value(0, output_field=money_field)),
        )
        .order_by("account__account_type", "account__code")
    )

    income = []
    expense = []
    total_income = DECIMAL_ZERO
    total_expense = DECIMAL_ZERO

    for r in by_account:
        acc_type = r["account__account_type"]
        debit = _d(r["debit"])
        credit = _d(r["credit"])

        if acc_type == LedgerAccount.AccountType.INCOME:
            amount = credit - debit
            income.append(
                {
                    "account_id": r["account_id"],
                    "code": r["account__code"],
                    "name": r["account__name"],
                    "amount": amount,
                }
            )
            total_income += amount
        else:
            amount = debit - credit
            expense.append(
                {
                    "account_id": r["account_id"],
                    "code": r["account__code"],
                    "name": r["account__name"],
                    "amount": amount,
                }
            )
            total_expense += amount

    return {
        "date_from": date_from,
        "date_to": date_to,
        "income": income,
        "expense": expense,
        "total_income": total_income,
        "total_expense": total_expense,
        "profit": total_income - total_expense,
    }


def balance_sheet(*, owner, as_of: date, pnl_from: Optional[date] = None):
    """
    Balance Sheet from GL.

    - Uses closing balances as of `as_of` (inclusive).
    - Optionally includes Net Profit from P&L (pnl_from..as_of) inside equity bucket.
    """
    money_field = DecimalField(max_digits=14, decimal_places=2)

    base = LedgerEntry.objects.filter(transaction__owner=owner, transaction__date__lte=as_of)
    by_account = (
        base.values("account_id", "account__code", "account__name", "account__account_type")
        .filter(account__account_type__in=[LedgerAccount.AccountType.ASSET, LedgerAccount.AccountType.LIABILITY, LedgerAccount.AccountType.EQUITY])
        .annotate(
            debit=Coalesce(Sum("debit"), Value(0, output_field=money_field)),
            credit=Coalesce(Sum("credit"), Value(0, output_field=money_field)),
        )
        .order_by("account__account_type", "account__code")
    )

    assets = []
    liabilities = []
    equity = []

    total_assets = DECIMAL_ZERO
    total_liabilities = DECIMAL_ZERO
    total_equity = DECIMAL_ZERO

    for r in by_account:
        net = _d(r["debit"]) - _d(r["credit"])  # DR - CR
        dr = net if net > 0 else DECIMAL_ZERO
        cr = (-net) if net < 0 else DECIMAL_ZERO

        item = {
            "account_id": r["account_id"],
            "code": r["account__code"],
            "name": r["account__name"],
            "debit": dr,
            "credit": cr,
        }

        acc_type = r["account__account_type"]
        if acc_type == LedgerAccount.AccountType.ASSET:
            assets.append(item)
            total_assets += dr - cr
        elif acc_type == LedgerAccount.AccountType.LIABILITY:
            liabilities.append(item)
            total_liabilities += cr - dr
        else:
            equity.append(item)
            total_equity += cr - dr

    net_profit = None
    if pnl_from:
        pnl = profit_and_loss(owner=owner, date_from=pnl_from, date_to=as_of)
        net_profit = _d(pnl["profit"])
        if net_profit != 0:
            # Add as a virtual equity line (Profit is a credit balance if positive)
            equity.append(
                {
                    "account_id": None,
                    "code": "NET_PROFIT",
                    "name": "Net Profit",
                    "debit": DECIMAL_ZERO if net_profit > 0 else (-net_profit),
                    "credit": net_profit if net_profit > 0 else DECIMAL_ZERO,
                }
            )
            if net_profit > 0:
                total_equity += net_profit
            else:
                total_equity -= (-net_profit)

    return {
        "as_of": as_of,
        "pnl_from": pnl_from,
        "assets": assets,
        "liabilities": liabilities,
        "equity": equity,
        "totals": {
            "assets": total_assets,
            "liabilities": total_liabilities,
            "equity": total_equity,
            "liabilities_plus_equity": total_liabilities + total_equity,
        },
        "net_profit": net_profit,
    }


def day_book(*, owner, date_from: date, date_to: date):
    """
    Day Book: voucher-wise list.
    """
    txns = (
        LedgerTransaction.objects.filter(owner=owner, date__gte=date_from, date__lte=date_to)
        .values("id", "date", "voucher_type", "reference_type", "reference_id", "reference_no", "narration", "total_debit")
        .order_by("date", "id")
    )
    return {"date_from": date_from, "date_to": date_to, "vouchers": list(txns)}


def ledger_statement(
    *,
    owner,
    account_code: Optional[str] = None,
    account_id: Optional[int] = None,
    party_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    if not account_id:
        if not account_code:
            raise ValueError("Provide account_id or account_code")
        acc = LedgerAccount.objects.filter(owner=owner, code=account_code).first()
        if not acc:
            return {"account": None, "entries": [], "running_balance": DECIMAL_ZERO}
        account_id = acc.id

    qs = LedgerEntry.objects.select_related("transaction", "account").filter(
        transaction__owner=owner,
        account_id=account_id,
    )
    if party_id:
        qs = qs.filter(party_id=party_id)
    if date_from:
        qs = qs.filter(transaction__date__gte=date_from)
    if date_to:
        qs = qs.filter(transaction__date__lte=date_to)

    qs = qs.order_by("transaction__date", "transaction_id", "line_no", "id")

    entries = []
    running = DECIMAL_ZERO

    for e in qs:
        running += _d(e.debit) - _d(e.credit)
        entries.append(
            {
                "date": e.transaction.date,
                "voucher_type": e.transaction.voucher_type,
                "reference_no": e.transaction.reference_no,
                "narration": e.transaction.narration,
                "description": e.description,
                "debit": _d(e.debit),
                "credit": _d(e.credit),
                "balance": running,
            }
        )

    account = LedgerAccount.objects.filter(id=account_id).values("id", "code", "name", "account_type").first()
    return {"account": account, "entries": entries, "running_balance": running}


def cash_book(*, owner, date_from: date, date_to: date):
    return ledger_statement(owner=owner, account_code="CASH", date_from=date_from, date_to=date_to)


def bank_book(*, owner, date_from: date, date_to: date):
    return ledger_statement(owner=owner, account_code="BANK", date_from=date_from, date_to=date_to)


def party_outstanding(*, owner, as_of: date):
    money_field = DecimalField(max_digits=14, decimal_places=2)

    # Party-ledger accounts only
    qs = (
        LedgerAccount.objects.filter(owner=owner, party__isnull=False)
        .values("party_id", "party__name", "party__party_type")
        .annotate(
            debit=Coalesce(Sum("entries__debit", filter=Q(entries__transaction__date__lte=as_of)), Value(0, output_field=money_field)),
            credit=Coalesce(Sum("entries__credit", filter=Q(entries__transaction__date__lte=as_of)), Value(0, output_field=money_field)),
        )
        .order_by("party__name")
    )

    receivables = []
    payables = []
    total_receivable = DECIMAL_ZERO
    total_payable = DECIMAL_ZERO

    for r in qs:
        net = _d(r["debit"]) - _d(r["credit"])  # +ve => receivable, -ve => payable (usually)
        item = {
            "party_id": r["party_id"],
            "party": r["party__name"],
            "party_type": r["party__party_type"],
            "balance": net,
        }
        if net >= 0:
            receivables.append(item)
            total_receivable += net
        else:
            payables.append(item)
            total_payable += (-net)

    return {
        "as_of": as_of,
        "receivables": receivables,
        "payables": payables,
        "totals": {"receivable": total_receivable, "payable": total_payable},
    }


def warehouse_stock(*, owner, as_of: date):
    """
    Closing stock computed ONLY from StockLedger (no stored stock fields).
    """
    money_field = DecimalField(max_digits=14, decimal_places=2)

    qs = (
        StockLedger.objects.filter(owner=owner, date__lte=as_of)
        .values("warehouse_id", "warehouse__name", "product_id", "product__name", "product__unit")
        .annotate(
            qty_in=Coalesce(Sum("quantity_in"), Value(0, output_field=money_field)),
            qty_out=Coalesce(Sum("quantity_out"), Value(0, output_field=money_field)),
        )
        .order_by("warehouse__name", "product__name")
    )

    rows = []
    for r in qs:
        closing = _d(r["qty_in"]) - _d(r["qty_out"])
        rows.append(
            {
                "warehouse_id": r["warehouse_id"],
                "warehouse": r["warehouse__name"] or "Unassigned",
                "product_id": r["product_id"],
                "product": r["product__name"],
                "unit": r["product__unit"],
                "qty_in": _d(r["qty_in"]),
                "qty_out": _d(r["qty_out"]),
                "closing_qty": closing,
            }
        )

    return {"as_of": as_of, "rows": rows}


def product_movement(
    *,
    owner,
    product_id: int,
    warehouse_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    qs = StockLedger.objects.filter(owner=owner, product_id=product_id)
    if warehouse_id:
        qs = qs.filter(warehouse_id=warehouse_id)
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)

    qs = qs.order_by("date", "id")

    rows = []
    running = DECIMAL_ZERO
    for e in qs:
        qty = _d(e.quantity_in) - _d(e.quantity_out)
        running += qty
        rows.append(
            {
                "date": e.date,
                "warehouse_id": e.warehouse_id,
                "movement": e.movement,
                "qty_in": _d(e.quantity_in),
                "qty_out": _d(e.quantity_out),
                "reference_type": e.reference_type,
                "reference_id": e.reference_id,
                "reference_line_id": e.reference_line_id,
                "running_qty": running,
            }
        )

    return {"product_id": product_id, "warehouse_id": warehouse_id, "rows": rows}


def gst_summary_gstr1_base(*, owner, date_from: date, date_to: date):
    """
    GST summary foundation (GSTR-1 base).

    Uses only GL postings:
    - Taxable value from SALES ledger credits
    - Output GST from OUTPUT_GST* ledger credits
    """
    txns = (
        LedgerTransaction.objects.filter(
            owner=owner,
            voucher_type=LedgerTransaction.VoucherType.SALES_INVOICE,
            date__gte=date_from,
            date__lte=date_to,
        )
        .prefetch_related("entries", "entries__account")
        .order_by("date", "id")
    )

    by_rate = defaultdict(lambda: {"taxable": DECIMAL_ZERO, "gst": DECIMAL_ZERO, "count": 0})
    invoices = []

    for t in txns:
        taxable = DECIMAL_ZERO
        gst = DECIMAL_ZERO
        gst_code = None

        for e in t.entries.all():
            code = getattr(e.account, "code", "")
            if code == "SALES":
                taxable += _d(e.credit) - _d(e.debit)
            if code.startswith("OUTPUT_GST"):
                gst += _d(e.credit) - _d(e.debit)
                gst_code = gst_code or code

        rate = None
        if gst_code and "_" in gst_code:
            try:
                rate = Decimal(gst_code.split("_", 1)[1])
            except Exception:
                rate = None

        key = str(rate) if rate is not None else "unknown"
        by_rate[key]["taxable"] += taxable
        by_rate[key]["gst"] += gst
        by_rate[key]["count"] += 1

        invoices.append(
            {
                "date": t.date,
                "invoice_no": t.reference_no,
                "taxable": taxable,
                "gst": gst,
                "gst_rate": rate,
            }
        )

    summary = [{"gst_rate": k, **v} for k, v in sorted(by_rate.items(), key=lambda x: x[0])]
    return {"date_from": date_from, "date_to": date_to, "summary": summary, "invoices": invoices}
