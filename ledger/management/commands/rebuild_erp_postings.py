from __future__ import annotations

import logging

from django.core.management.base import BaseCommand
from django.db.models import Q

from ledger.services.posting import (
    post_expense,
    post_invoice,
    post_journal_voucher,
    post_khata_transaction,
    post_payment,
    post_stock_transfer,
    post_supplier_payment,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Rebuild/sync ERP GL + StockLedger postings from existing source documents."

    def add_arguments(self, parser):
        parser.add_argument(
            "--owner-id",
            type=int,
            default=None,
            help="Limit rebuild to a specific user (tenant).",
        )

    def handle(self, *args, **options):
        owner_id = options.get("owner_id")

        from accounts.models import Expense
        from commerce.models import Invoice, Payment
        from khataapp.models import SupplierPayment, Transaction as KhataTxn
        from ledger.models import JournalVoucher, StockTransfer

        self.stdout.write(self.style.WARNING("Rebuilding ERP postings..."))

        # Invoices (also rebuilds StockLedger)
        inv_qs = Invoice.objects.all()
        if owner_id:
            inv_qs = inv_qs.filter(Q(order__owner_id=owner_id) | Q(order__party__owner_id=owner_id))
        inv_ids = inv_qs.values_list("id", flat=True).order_by("id").iterator()
        for inv_id in inv_ids:
            try:
                post_invoice(int(inv_id))
            except Exception:
                logger.exception("Failed posting invoice id=%s", inv_id)

        # Payments
        pay_qs = Payment.objects.all()
        if owner_id:
            pay_qs = pay_qs.filter(Q(invoice__order__owner_id=owner_id) | Q(invoice__order__party__owner_id=owner_id))
        pay_ids = pay_qs.values_list("id", flat=True).order_by("id").iterator()
        for pay_id in pay_ids:
            try:
                post_payment(int(pay_id))
            except Exception:
                logger.exception("Failed posting payment id=%s", pay_id)

        # Manual khata transactions
        txn_qs = KhataTxn.objects.all()
        if owner_id:
            txn_qs = txn_qs.filter(party__owner_id=owner_id)
        txn_ids = txn_qs.values_list("id", flat=True).order_by("id").iterator()
        for txn_id in txn_ids:
            try:
                post_khata_transaction(int(txn_id))
            except Exception:
                logger.exception("Failed posting khata transaction id=%s", txn_id)

        # Expenses
        exp_qs = Expense.objects.all()
        if owner_id:
            exp_qs = exp_qs.filter(created_by_id=owner_id)
        exp_ids = exp_qs.values_list("id", flat=True).order_by("id").iterator()
        for exp_id in exp_ids:
            try:
                post_expense(int(exp_id))
            except Exception:
                logger.exception("Failed posting expense id=%s", exp_id)

        # Supplier payments
        sp_qs = SupplierPayment.objects.all()
        if owner_id:
            sp_qs = sp_qs.filter(Q(order__owner_id=owner_id) | Q(supplier__owner_id=owner_id))
        sp_ids = sp_qs.values_list("id", flat=True).order_by("id").iterator()
        for sp_id in sp_ids:
            try:
                post_supplier_payment(int(sp_id))
            except Exception:
                logger.exception("Failed posting supplier payment id=%s", sp_id)

        # Stock transfers
        st_qs = StockTransfer.objects.all()
        if owner_id:
            st_qs = st_qs.filter(owner_id=owner_id)
        st_ids = st_qs.values_list("id", flat=True).order_by("id").iterator()
        for st_id in st_ids:
            try:
                post_stock_transfer(int(st_id))
            except Exception:
                logger.exception("Failed posting stock transfer id=%s", st_id)

        # Journal vouchers
        jv_qs = JournalVoucher.objects.all()
        if owner_id:
            jv_qs = jv_qs.filter(owner_id=owner_id)
        jv_ids = jv_qs.values_list("id", flat=True).order_by("id").iterator()
        for jv_id in jv_ids:
            try:
                post_journal_voucher(int(jv_id))
            except Exception:
                logger.exception("Failed posting journal voucher id=%s", jv_id)

        self.stdout.write(self.style.SUCCESS("ERP postings rebuild completed."))
