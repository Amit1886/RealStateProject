from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.db.models import Sum


def _fixed_dashboard_factory():
    # Import lazily to avoid import-order issues.
    import accounts.views as av

    Decimal = av.Decimal
    now = av.now
    timedelta = av.timedelta
    datetime = av.datetime
    build_business_snapshot = av.build_business_snapshot

    Party = av.Party
    Transaction = av.Transaction
    Invoice = av.Invoice
    Payment = av.Payment
    Coupon = av.Coupon
    UserCoupon = av.UserCoupon
    UserProfile = av.UserProfile
    render = av.render

    update_daily_summary = getattr(av, "update_daily_summary", None)

    @login_required
    def fixed_dashboard(request):
        user = request.user

        period = request.GET.get("period", "today")
        today = now().date()

        if period == "yesterday":
            selected_date = today - timedelta(days=1)
        elif period == "month":
            selected_date = today.replace(day=1)
        else:
            selected_date = today

        snapshot = build_business_snapshot(user, selected_date)

        hour = datetime.now().hour
        if hour < 12:
            greeting = "Good Morning"
        elif hour < 17:
            greeting = "Good Afternoon"
        else:
            greeting = "Good Evening"

        profile, _ = UserProfile.objects.get_or_create(user=user)
        summary = update_daily_summary(user) if callable(update_daily_summary) else None

        recent_parties = Party.objects.filter(owner=user).order_by("-id")[:5]
        recent_transactions = Transaction.objects.filter(party__owner=user).order_by("-id")[:5]

        total_credit_all = (
            Transaction.objects.filter(party__owner=user, txn_type="credit").aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )
        total_debit_all = (
            Transaction.objects.filter(party__owner=user, txn_type="debit").aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )
        net_balance = total_debit_all - total_credit_all

        party_cards = []
        for party in Party.objects.filter(owner=user).order_by("name"):
            party_cash_credit = (
                Transaction.objects.filter(party=party, txn_type="credit").aggregate(total=Sum("amount"))["total"]
                or Decimal("0.00")
            )
            party_cash_debit = (
                Transaction.objects.filter(party=party, txn_type="debit").aggregate(total=Sum("amount"))["total"]
                or Decimal("0.00")
            )

            invoice_total = (
                Invoice.objects.filter(order__party=party).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
            )
            payment_total = (
                Payment.objects.filter(invoice__order__party=party).aggregate(total=Sum("amount"))["total"]
                or Decimal("0.00")
            )

            p_total_debit = Decimal(invoice_total) + Decimal(party_cash_debit)
            p_total_credit = Decimal(payment_total) + Decimal(party_cash_credit)
            p_balance = p_total_debit - p_total_credit

            party_cards.append(
                {"party": party, "total_debit": p_total_debit, "total_credit": p_total_credit, "balance": p_balance}
            )

        active_coupons = Coupon.objects.filter(is_active=True).order_by("-created_at")[:10]
        user_coupons = UserCoupon.objects.filter(user=user).select_related("coupon")

        context = {
            "user": user,
            "profile": profile,
            "recent_parties": recent_parties,
            "recent_transactions": recent_transactions,
            "total_credit": total_credit_all,
            "total_debit": total_debit_all,
            "net_balance": net_balance,
            "party_cards": party_cards,
            "summary": summary,
            "snapshot": snapshot,
            "period": period,
            "greeting": greeting,
            "active_coupons": active_coupons,
            "user_coupons": user_coupons,
        }
        return render(request, "accounts/dashboard.html", context)

    fixed_dashboard._addons_hotfix_patched = True
    return fixed_dashboard


def patch_accounts_dashboard_urlpattern() -> None:
    try:
        import accounts.urls as au
    except Exception:
        return

    try:
        fixed_dashboard = _fixed_dashboard_factory()
    except Exception:
        return

    for p in getattr(au, "urlpatterns", []):
        if getattr(p, "name", None) == "dashboard":
            try:
                # URLPattern stores the callable in _callback; urls.py already holds an older
                # login_required closure so replacing accounts.views.dashboard isn't enough.
                p._callback = fixed_dashboard  # noqa: SLF001
            except Exception:
                pass


patch_accounts_dashboard_urlpattern()
