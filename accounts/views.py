from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, authenticate, get_user_model, logout
from django.contrib.auth import get_backends
from django.db import transaction
from django.db.models import Sum
from django.core.paginator import Paginator, EmptyPage
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from decimal import Decimal
from django.db.models import Case, When, F, FloatField
from django.http import HttpResponseForbidden
from .models import DailySummary
from khataapp.models import Transaction
from django.utils.timezone import now
from datetime import timedelta
# accounts/views.py

from accounts.services.snapshot import build_business_snapshot
from .models import Expense, ExpenseCategory
import uuid
from khataapp.models import UserProfile as KhataProfile
from django.conf import settings



# Accounts
from datetime import datetime, date
from .models import  OTP, LedgerEntry
from .utils import render_to_pdf_bytes, send_email_otp, send_sms_otp
from .forms import SignupForm, LoginForm, OTPForm, UserProfileForm

# External Models
from khataapp.models import Party, UserProfile
from billing.models import Plan, Subscription
from commerce.models import Order, Payment, Invoice, Coupon, UserCoupon


User = get_user_model()

def calculate_running_balance(entries):
    balance = 0

    for e in entries:
        amount = e.get("amount", 0)

        # Debit = positive
        # Credit = negative
        if amount > 0:
            e["debit"] = amount
            e["credit"] = 0
        else:
            e["debit"] = 0
            e["credit"] = abs(amount)

        # Running balance (Busy style)
        balance += amount
        e["balance"] = balance

    return entries
# ---------------------------------------------------
# WhatsApp Message URL Builder
# ---------------------------------------------------
def whatsapp_message_url(mobile, text):
    import urllib.parse
    return f"https://wa.me/91{mobile}?text={urllib.parse.quote(text)}"

def users_list(request):
    admin_users = User.objects.filter(is_staff=True)  # admin users
    signup_users = User.objects.filter(is_staff=False)  # users created from signup
    profiles = UserProfile.objects.all()  # profile data if needed

    context = {
        "admin_users": admin_users,
        "signup_users": signup_users,
        "profiles": profiles,
    }
    return render(request, "accounts/users_list.html", context)

# ----------------- DASHBOARD -----------------
@login_required
def dashboard(request):
    user = request.user
    # 🔥 BUSINESS SNAPSHOT (TODAY)
    snapshot = build_business_snapshot(request.user, now().date())
    period = request.GET.get("period", "today")
    today = now().date()

    if period == "yesterday":
        selected_date = today - timedelta(days=1)

    elif period == "month":
        selected_date = today.replace(day=1)

    else:
        selected_date = today

    snapshot = build_business_snapshot(request.user, selected_date)

 # --- Greeting logic ---
    hour = datetime.now().hour
    if hour < 12:
        greeting = "Good Morning"
    elif hour < 17:
        greeting = "Good Afternoon"
    else:
        greeting = "Good Evening"

         # --- Profile fetch (THIS WAS MISSING) ---
    profile, _ = UserProfile.objects.get_or_create(user=request.user)


    # Daily Summary Update
    summary = update_daily_summary(user)

    profile = UserProfile.objects.filter(user=user).first()

    recent_parties = Party.objects.filter(owner=user).order_by("-id")[:5]
    recent_transactions = Transaction.objects.filter(
        party__owner=user
    ).order_by("-id")[:5]

    total_credit_all = Transaction.objects.filter(
        party__owner=user, txn_type="credit"
    ).aggregate(total=Sum("amount"))["total"] or 0

    total_debit_all = Transaction.objects.filter(
        party__owner=user, txn_type="debit"
    ).aggregate(total=Sum("amount"))["total"] or 0

    net_balance = total_debit_all - total_credit_all

    # PARTY CARDS
    party_cards = []
    parties = Party.objects.filter(owner=user).order_by("name")

    for party in parties:

        party_cash_credit = Transaction.objects.filter(
            party=party, txn_type='credit'
        ).aggregate(total=Sum('amount'))['total'] or 0

        party_cash_debit = Transaction.objects.filter(
            party=party, txn_type='debit'
        ).aggregate(total=Sum('amount'))['total'] or 0

        invoice_total = Invoice.objects.filter(
            order__party=party
        ).aggregate(total=Sum('amount'))['total'] or 0

        payment_total = Payment.objects.filter(
            invoice__order__party=party
        ).aggregate(total=Sum('amount'))['total'] or 0

        p_total_debit = invoice_total + party_cash_debit
        p_total_credit = payment_total + party_cash_credit
        p_balance = p_total_debit - p_total_credit

    party_cards.append({
            "party": party,
            "total_debit": p_total_debit,
            "total_credit": p_total_credit,
            "balance": p_balance,
        })

    # COUPON DATA
    active_coupons = Coupon.objects.filter(is_active=True).order_by("-created_at")[:10]
    user_coupons = UserCoupon.objects.filter(user=request.user).select_related('coupon')

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

# -----------------------------------------
# Party ledger: main view (with filters)
# -----------------------------------------
# --- SUMMARY FUNCTION FOR DASHBOARD ---
def get_party_summary(party):
    orders = Order.objects.filter(party=party)
    invoices = Invoice.objects.filter(order__party=party)
    payments = Payment.objects.filter(invoice__order__party=party)
    txns = Transaction.objects.filter(party=party)

    total_debit = Decimal("0.00")
    total_credit = Decimal("0.00")

    # Orders
    for o in orders:
        amount = o.total_amount() if hasattr(o, "total_amount") else Decimal("0.00")
        total_debit += amount

    # Invoices
    for inv in invoices:
        total_debit += inv.amount

    # Payments
    for p in payments:
        total_credit += p.amount

    # Manual Txns
    for t in txns:
        if t.txn_type == "debit":
            total_debit += t.amount
        else:
            total_credit += t.amount

    balance = total_debit - total_credit

    return {
        "debit": total_debit,
        "credit": total_credit,
        "balance": balance,
    }

# ---------------------------------------------------
# Helper to normalize dates
# ---------------------------------------------------
def normalize_date(d):
    # If already date, return
    if isinstance(d, date) and not isinstance(d, datetime):
        return d

    # If datetime, convert to date
    if isinstance(d, datetime):
        return d.date()

    # If string, convert safely
    try:
        return datetime.strptime(d, "%Y-%m-%d").date()
    except:
        try:
            return datetime.strptime(d, "%Y-%m-%d %H:%M:%S").date()
        except:
            return date.today()  # fallback)

# ---------------------------------------------------
# Party Ledger (Busy-Style with Running Balance)
# ---------------------------------------------------
@login_required
def party_ledger(request, party_id):

    party = get_object_or_404(Party, id=party_id, owner=request.user)

    # --------------------------
    # DATE FILTERS
    # --------------------------
    date_from = request.GET.get("from")
    date_to = request.GET.get("to")

    orders = Order.objects.filter(party=party)
    invoices = Invoice.objects.filter(order__party=party)
    payments = Payment.objects.filter(invoice__order__party=party)
    txns = Transaction.objects.filter(party=party)

    # Apply date filters
    if date_from:
        df = datetime.fromisoformat(date_from).date()
        orders = orders.filter(created_at__date__gte=df)
        invoices = invoices.filter(created_at__date__gte=df)
        payments = payments.filter(created_at__date__gte=df)
        txns = txns.filter(date__gte=df)

    if date_to:
        dt = datetime.fromisoformat(date_to).date()
        orders = orders.filter(created_at__date__lte=dt)
        invoices = invoices.filter(created_at__date__lte=dt)
        payments = payments.filter(created_at__date__lte=dt)
        txns = txns.filter(date__lte=dt)

    # --------------------------
    # LEDGER ENTRY LIST
    # --------------------------
    entries = []

    # ---- ORDERS ----
    for order in orders:
        entries.append({
            "date": order.created_at.date(),
            "type": "Order",
            "invoice_no": "",
            "description": f"Order #{order.id}",
            "debit": 0,
            "credit": 0,
        })

    # ---- INVOICES (DEBIT) ----
    for invoice in invoices:
        entries.append({
            "date": invoice.created_at.date(),
            "type": "Invoice",
            "invoice_no": invoice.number,
            "description": f"Invoice {invoice.number}",
            "debit": float(invoice.amount),
            "credit": 0,
        })

    # ---- PAYMENTS (CREDIT) ----
    for payment in payments:
        entries.append({
            "date": payment.created_at.date(),
            "type": "Payment",
            "invoice_no": "",
            "description": payment.method,
            "debit": 0,
            "credit": float(payment.amount),
        })

    # ---- MANUAL TRANSACTIONS ----
    for t in txns:
        debit = float(t.amount) if t.txn_type == "debit" else 0
        credit = float(t.amount) if t.txn_type == "credit" else 0

        entries.append({
            "date": t.date,
            "type": "Txn",
            "invoice_no": "",
            "description": t.notes or "Transaction",
            "debit": debit,
            "credit": credit,
        })

    # --------------------------
    # SORT BY DATE ASCENDING
    # --------------------------
    entries.sort(key=lambda x: x["date"])

    # --------------------------
    # RUNNING BALANCE
    # --------------------------
    balance = 0
    for e in entries:
        balance += e["debit"] - e["credit"]
        e["balance"] = balance

    # --------------------------
    # REVERSE FOR UI
    # --------------------------
    entries.reverse()

    # --------------------------
    # PAGINATION
    # --------------------------
    paginator = Paginator(entries, 15)
    page = int(request.GET.get("page", 1))

    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    # --------------------------
    # TOTALS
    # --------------------------
    total_debit = sum(e["debit"] for e in entries)
    total_credit = sum(e["credit"] for e in entries)
    final_balance = total_debit - total_credit

    # --------------------------
    # CONTEXT
    # --------------------------
    context = {
        "party": party,
        "entries": page_obj.object_list,
        "page_obj": page_obj,
        "paginator": paginator,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "balance": final_balance,
        "whatsapp_url": whatsapp_message_url(
            party.mobile,
            f"Your current balance is ₹{final_balance}"
        ),
    }

    return render(request, "accounts/party_ledger.html", context)

def ledger_list(request):
    # parties owned by current user
    parties = Party.objects.filter(owner=request.user)

    selected_party = request.GET.get("party_id")
    qs = LedgerEntry.objects.none()

    totals = {"total_debit": 0, "total_credit": 0, "balance": 0}

    if selected_party:

        # ---- IMPORTANT FIX: party ownership check ----
        party = Party.objects.filter(id=selected_party, owner=request.user).first()
        if not party:
            return HttpResponseForbidden("You do not have permission to view this party.")

        qs = LedgerEntry.objects.filter(
            account__user=request.user,
            party=party
        ).order_by("date", "id")

        totals = qs.aggregate(
            total_debit=Sum(Case(
                When(txn_type="debit", then=F("amount")),
                default=0,
                output_field=FloatField(),
            )),
            total_credit=Sum(Case(
                When(txn_type="credit", then=F("amount")),
                default=0,
                output_field=FloatField(),
            )),
        )

        totals["balance"] = (totals["total_credit"] or 0) - (totals["total_debit"] or 0)

    return render(request, "accounts/ledger_list.html", {
        "parties": parties,
        "entries": qs,
        "selected_party": selected_party,
        "totals": totals,
    })

#---------------------------------------------------
# AJAX Load More (Busy style)
# ---------------------------------------------------
@login_required
def party_ledger_load_more(request, party_id):

    if request.headers.get('x-requested-with') != 'XMLHttpRequest':
        return JsonResponse({"error": "Only AJAX allowed"}, status=400)

    party = get_object_or_404(Party, id=party_id, owner=request.user)

    ledger_qs = LedgerEntry.objects.filter(party=party).order_by("date", "id")

    # Convert to dict list
    entries = []
    running_balance = 0

    for e in ledger_qs:
        running_balance += e.credit - e.debit

        entries.append({
            "date": e.date,
            "invoice": e.invoice_no or "-",
            "desc": e.description or e.notes or "",
            "credit": e.credit,
            "debit": e.debit,
            "balance": running_balance,
            "type": e.source,
        })

    entries.reverse()

    page = int(request.GET.get("page", 1))
    paginator = Paginator(entries, 20)

    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        return JsonResponse({"html": "", "has_next": False})

    html = render_to_string("accounts/ledger_entries.html", {
        "entries": page_obj.object_list
    })

    return JsonResponse({"html": html, "has_next": page_obj.has_next()})


# ---------------------------------------------------
# PDF Export – Busy Format
# ---------------------------------------------------
@login_required
def party_ledger_pdf(request, party_id):

    party = get_object_or_404(Party, id=party_id, owner=request.user)

    ledger_qs = LedgerEntry.objects.filter(party=party).order_by("date", "id")

    entries = []
    running_balance = 0

    for e in ledger_qs:
        running_balance += e.credit - e.debit

        entries.append({
            "date": e.date.date(),
            "invoice": e.invoice_no or "-",
            "desc": e.description or e.notes or "",
            "credit": e.credit,
            "debit": e.debit,
            "balance": running_balance,
            "type": e.source,
        })

    total_credit = sum(e['credit'] for e in entries)
    total_debit = sum(e['debit'] for e in entries)
    final_balance = total_credit - total_debit

    context = {
        "party": party,
        "entries": entries,
        "total_credit": total_credit,
        "total_debit": total_debit,
        "balance": final_balance,
        "generated_on": timezone.now(),
    }

    pdf_bytes = render_to_pdf_bytes("accounts/party_ledger_pdf.html", context)

    if pdf_bytes:
        resp = HttpResponse(pdf_bytes, content_type="application/pdf")
        resp['Content-Disposition'] = f'attachment; filename="ledger_{party.id}.pdf"'
        return resp

    # fallback if pdf generation fails
    return render(request, "accounts/party_ledger_pdf.html", context)

@login_required
def staff_dashboard(request):
    return render(request, "accounts/staff_dashboard.html")

# ----------------- EDIT PROFILE -----------------
@login_required
def edit_profile(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if not profile.plan:
        basic_plan = Plan.objects.filter(name__iexact="Basic").first()
        if basic_plan:
            profile.plan = basic_plan
            profile.save()

    if request.method == "POST":
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            selected_plan = form.cleaned_data.get("plan")
            user = request.user
            user.email = form.cleaned_data.get("email", user.email)
            user.first_name = form.cleaned_data.get("full_name", user.first_name)
            user.save(update_fields=["email", "first_name"])
            form.save()

            if selected_plan and selected_plan.name.lower() != "basic":
                has_active = Subscription.objects.filter(
                    user=request.user, plan=selected_plan, status="active"
                ).exists()
                if not has_active:
                    messages.info(request, f"Redirecting to payment for {selected_plan.name} plan...")
                    return redirect(f"/billing/checkout/?plan_id={selected_plan.id}")

            messages.success(request, "🎉 Profile updated successfully!")
            return redirect("accounts:edit_profile")
        else:
            messages.error(request, "⚠️ Please correct the errors below.")
    else:
        form = UserProfileForm(instance=profile)

    admin_profile = UserProfile.objects.filter(user__is_superuser=True).first()
    context = {
        "form": form,
        "profile": profile,
        "admin_logo": admin_profile.profile_picture.url if admin_profile and admin_profile.profile_picture else None,
        "admin_name": admin_profile.business_name if admin_profile else "",
        "admin_address": admin_profile.address if admin_profile else "",
        "admin_gst": admin_profile.gst_number if admin_profile else "",
        "admin_contact": admin_profile.mobile if admin_profile else "",
        "plan_name": profile.plan.name if profile.plan else "Basic",
    }

    return render(request, "accounts/edit_profile.html", context)

# ----------------- SIGNUP -----------------
def signup_view(request):
    if request.method == "POST":
        form = SignupForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save(commit=False)
                    user.is_active = False
                    user.save()

                    otp = OTP.create_for(
                        user=user,
                        purpose="signup",
                        email=user.email,
                        mobile=form.cleaned_data.get("mobile"),
                    )

                # Create khataapp profile OUTSIDE transaction to avoid FK constraint issues
                try:
                    profile = KhataProfile.objects.get(user=user)
                except KhataProfile.DoesNotExist:
                    profile = KhataProfile.objects.create(
                        user=user,
                        created_from="signup",
                        plan=None,
                        mobile=form.cleaned_data.get("mobile"),
                        full_name=user.get_full_name() or user.username
                    )

                # OTP sending outside transaction
                if user.email:
                    send_email_otp(user.email, otp.code)
                if profile.mobile:
                    send_sms_otp(profile.mobile, otp.code)

                request.session["otp_user_id"] = user.id
                request.session["otp_purpose"] = "signup"

                messages.success(request, "OTP sent. Please verify your account.")
                return redirect("accounts:verify_otp")

            except Exception as e:
                messages.error(request, f"Signup failed: {e}")
                return redirect("accounts:signup")

    else:
        form = SignupForm()

    return render(request, "accounts/signup.html", {"form": form})

# ----------------- LOGIN -----------------
def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            identifier = form.cleaned_data["identifier"]
            password = form.cleaned_data["password"]
            use_otp = form.cleaned_data.get("use_otp", True)

            # Find user by mobile or email
            user = None
            mobile_for_otp = None
            
            profile = KhataProfile.objects.filter(mobile=identifier).select_related("user").first()
            if profile:
                user = profile.user
                mobile_for_otp = profile.mobile
            else:
                # Try to find user by email
                try:
                    user = User.objects.get(email__iexact=identifier)
                    # Get mobile from user's profile if exists
                    user_profile = KhataProfile.objects.filter(user=user).first()
                    mobile_for_otp = user_profile.mobile if user_profile else None
                except User.DoesNotExist:
                    messages.error(request, "User not found")
                    return render(request, "accounts/login.html", {"form": form})

            # Ensure user is not None before proceeding
            if not user:
                messages.error(request, "User not found")
                return render(request, "accounts/login.html", {"form": form})

            # ---- OTP LOGIN ----
            if use_otp:
                otp = OTP.create_for(
                    user=user,
                    purpose="login",
                    email=user.email,
                    mobile=mobile_for_otp,
                )

                if user.email:
                    send_email_otp(user.email, otp.code)
                if mobile_for_otp:
                    send_sms_otp(mobile_for_otp, otp.code)

                request.session["otp_user_id"] = user.id
                request.session["otp_purpose"] = "login"

                messages.info(request, "OTP sent. Please verify.")
                return redirect("accounts:verify_otp")

            # ---- NORMAL PASSWORD LOGIN ----
            user_auth = authenticate(username=user.username, password=password)
            if user_auth and not user_auth.is_active:
                messages.error(request, "Verify OTP first")
                request.session["otp_user_id"] = user.id
                return redirect("accounts:verify_otp")
            else:
                messages.error(request, "Invalid credentials")

    else:
        form = LoginForm()

    return render(request, "accounts/login.html", {"form": form})


# ----------------- OTP VERIFY -----------------
def verify_otp_view(request):

    user_id = request.session.get("otp_user_id")

    if not user_id:
        messages.error(request, "Session expired. Please login again.")
        return redirect("accounts:login")

    user = get_object_or_404(User, id=user_id)

    # ✅ TEMPORARY BYPASS (Render free deploy helper)
    if getattr(settings, "OTP_BYPASS", False):
        user.is_active = True
        user.is_otp_verified = True
        user.save(update_fields=["is_active", "is_otp_verified"])

        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)

        request.session.pop("otp_user_id", None)
        request.session.pop("otp_purpose", None)

        messages.warning(request, "⚠ OTP bypass mode active (temporary).")

        if user.is_superuser:
            return redirect("/superadmin/")
        return redirect("/accounts/dashboard/")


    # ✅ NORMAL FLOW (PRODUCTION SAFE)
    if request.method == "POST":
        form = OTPForm(request.POST)

        if form.is_valid():
            code = form.cleaned_data["code"]

            otp = OTP.objects.filter(
                user=user,
                verified=False,
                expires_at__gte=timezone.now()
            ).order_by("-created_at").first()

            if not otp:
                messages.error(request, "OTP expired. Please resend.")
                return redirect("accounts:verify_otp")

            if otp.code != code:
                messages.error(request, "Invalid OTP.")
                return redirect("accounts:verify_otp")

            otp.verified = True
            otp.save(update_fields=["verified"])

            user.is_active = True
            user.is_otp_verified = True
            user.save(update_fields=["is_active", "is_otp_verified"])

            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)

            request.session.pop("otp_user_id", None)
            request.session.pop("otp_purpose", None)

            messages.success(request, "Account verified successfully.")

            if user.is_superuser:
                return redirect("/superadmin/")
            else:
                return redirect("/accounts/dashboard/")

    else:
        form = OTPForm()

    return render(request, "accounts/verify_otp.html", {
        "form": form,
        "user": user
    })


# ----------------- LOGOUT -----------------
def logout_view(request):
    logout(request)
    return redirect("accounts:login")


# ----------------- PROFILE SETTINGS (Legacy Support) -----------------
@login_required
def profile_settings(request):
    """Optional: keep for backward compatibility"""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("accounts:dashboard")
    else:
        form = UserProfileForm(instance=profile)

    return render(request, "accounts/profile_settings.html", {"form": form})


# ----------------- SUBSCRIBE PLAN -----------------
@login_required
def subscribe_plan(request, plan_id):
    plan = get_object_or_404(Plan, id=plan_id)
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    profile.plan = plan
    profile.save()
    messages.success(request, f"Subscribed to {plan.name} plan.")
    return redirect("accounts:dashboard")

@login_required
def upgrade_plan(request, plan_id):
    plan = get_object_or_404(Plan, id=plan_id)
    user = request.user

    # ✅ Create unpaid invoice
    invoice = Invoice.objects.create(
        user=user,
        plan=plan,
        amount=plan.price_per_month,
        status="pending"
    )

    # Redirect to your payment gateway (Razorpay, Stripe, etc.)
    return redirect(f"/billing/pay/{invoice.id}/")

@login_required
def daily_summary_view(request):
    user = request.user

    # Always ensure user is a valid User object
    if not isinstance(user, User):
        user = User.objects.filter(username=user).first()
        if not user:
            return HttpResponse("Invalid user. Contact admin.")

    today = date.today()

    summary = DailySummary.objects.filter(user=user, date=today).first()

    if summary is None:
        transactions = Transaction.objects.filter(
            party__owner=user,
            date=today
        )

        total_debit = transactions.filter(txn_type="debit").aggregate(total=Sum("amount"))["total"] or 0
        total_credit = transactions.filter(txn_type="credit").aggregate(total=Sum("amount"))["total"] or 0

        balance = total_debit - total_credit

        summary = DailySummary.objects.create(
            user=user,
            date=today,
            total_credit=total_credit,
            total_debit=total_debit,
            balance=balance,
            total_transactions=transactions.count(),
        )

    return render(request, "accounts/daily_summary.html", {"summary": summary})


# -------------------------------------------------------
# SAFE UPDATE FUNCTION – WILL NEVER CRASH OR TAKE STRING
# -------------------------------------------------------

def update_daily_summary(user):

    # 1. Convert anything to User object safely
    if isinstance(user, User):
        pass
    elif isinstance(user, int):
        user = User.objects.filter(id=user).first()
    elif isinstance(user, str):
        user = User.objects.filter(username=user).first()
    else:
        return None

    if not user:
        return None

    today = timezone.now().date()

    transactions = Transaction.objects.filter(
        party__owner=user,
        date=today
    )

    total_credit = transactions.filter(txn_type='credit').aggregate(total=Sum('amount'))['total'] or 0
    total_debit = transactions.filter(txn_type='debit').aggregate(total=Sum('amount'))['total'] or 0
    balance = total_debit - total_credit

    summary, created = DailySummary.objects.get_or_create(
        user=user,
        date=today,
        defaults={
            'total_credit': total_credit,
            'total_debit': total_debit,
            'balance': balance,
            'total_transactions': transactions.count(),
        }
    )

    summary.total_credit = total_credit
    summary.total_debit = total_debit
    summary.balance = balance
    summary.total_transactions = transactions.count()
    summary.save()

    return summary

@login_required
def business_snapshot_view(request):
    snapshot = build_business_snapshot(request.user)
    return render(
        request,
        "accounts/business_snapshot.html",
        {"snapshot": snapshot}
    )

# -------------------------------------------------------
# SAFE UPDATE FUNCTION – WILL NEVER CRASH OR TAKE STRING
# -------------------------------------------------------
@login_required
def create_expense(request):
    categories = ExpenseCategory.objects.filter(created_by=request.user)

    if request.method == "POST":
        category_name = request.POST.get("new_category")
        category_id = request.POST.get("category")
        expense_date = request.POST.get("expense_date")
        description = request.POST.get("description")
        amount_paid = request.POST.get("amount_paid")

        if category_name:
            category = ExpenseCategory.objects.create(
                name=category_name,
                created_by=request.user
            )
        else:
            category = ExpenseCategory.objects.get(id=category_id)

        Expense.objects.create(
            expense_number=f"EXP-{uuid.uuid4().hex[:6].upper()}",
            expense_date=expense_date,
            category=category,
            description=description,
            amount_paid=amount_paid,
            created_by=request.user
        )

        return redirect("accounts:expense_list")

    return render(request, "accounts/expense_create.html", {
        "categories": categories,
        "today": now().date()
    })

@login_required
def expense_list(request):
    expenses = Expense.objects.filter(created_by=request.user).order_by("-expense_date")
    return render(request, "accounts/expense_list.html", {
        "expenses": expenses
    })
    

