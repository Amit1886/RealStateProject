# /home/Khataapp/myproject/khatapro/accounts/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate, get_backends
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from .models import User, OTP, UserProfile, Plan
from .forms import SignupForm, LoginForm, OTPForm
from .utils import send_email_otp, send_sms_otp
from khataapp.models import Transaction, Party


# ---------------- SIGNUP ----------------
def signup_view(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.save()

            # Assign default free plan
            free_plan = Plan.objects.filter(is_free=True).first()
            if free_plan:
                UserProfile.objects.create(user=user, plan=free_plan)

            otp = OTP.create_for(user, "signup", email=user.email, mobile=user.mobile)
            if user.email:
                send_email_otp(user.email, otp.code)
            if user.mobile:
                send_sms_otp(user.mobile, otp.code)

            request.session["otp_user_id"] = user.id
            request.session["otp_purpose"] = "signup"
            return redirect("accounts:verify_otp")
    else:
        form = SignupForm()
    return render(request, "accounts/signup.html", {"form": form})


# ---------------- LOGIN ----------------
def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            ident = form.cleaned_data["identifier"].strip()
            use_otp = form.cleaned_data["use_otp"]
            user = None

            # Identify user by email or mobile
            if "@" in ident:
                user = User.objects.filter(email__iexact=ident).first()
            else:
                user = User.objects.filter(mobile=ident).first()

            if not user:
                messages.error(request, "User not found.")
            else:
                if use_otp:
                    otp = OTP.create_for(user, "login", email=user.email, mobile=user.mobile)
                    if user.email:
                        send_email_otp(user.email, otp.code)
                    if user.mobile:
                        send_sms_otp(user.mobile, otp.code)
                    request.session["otp_user_id"] = user.id
                    request.session["otp_purpose"] = "login"
                    return redirect("accounts:verify_otp")
                else:
                    pwd = form.cleaned_data["password"]
                    u = authenticate(request, username=user.username, password=pwd)
                    if u:
                        login(request, u)
                        return redirect("accounts:dashboard")
                    messages.error(request, "Invalid credentials.")
    else:
        form = LoginForm()
    return render(request, "accounts/login.html", {"form": form})


# ---------------- COMPLETE PROFILE ----------------
@login_required
def complete_profile(request):
    # Account side profile
    acc_profile, _ = UserProfile.objects.get_or_create(user=request.user)

    # Khataapp side profile
    from khataapp.models import UserProfile as KhataProfile
    kha_profile, _ = KhataProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        mobile = request.POST.get("mobile")
        name = request.POST.get("name")
        otp_verified = True  # maan lo OTP verify ho gaya

        # update accounts profile
        acc_profile.mobile = mobile
        acc_profile.otp_verified = otp_verified
        acc_profile.save()

        # update khataapp profile
        if name:
            kha_profile.name = name
        if mobile:
            kha_profile.mobile = mobile
        kha_profile.save()

        messages.success(request, "Profile updated successfully.")
        return redirect("accounts:dashboard")

    return render(request, "accounts/complete_profile.html", {
        "acc_profile": acc_profile,
        "kha_profile": kha_profile,
    })


# ---------------- VERIFY OTP ----------------
def verify_otp_view(request):
    user_id = request.session.get("otp_user_id")
    purpose = request.session.get("otp_purpose")

    if not user_id or not purpose:
        messages.error(request, "OTP session expired.")
        return redirect("accounts:login")

    user = User.objects.filter(id=user_id).first()
    if not user:
        messages.error(request, "User not found.")
        return redirect("accounts:login")

    if request.method == "POST":
        form = OTPForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["code"].strip()
            otp = OTP.objects.filter(user=user, purpose=purpose).order_by("-created_at").first()

            if otp and otp.is_valid(code):
                # Update verification flags
                if purpose == "signup":
                    if otp.sent_to_email:
                        user.email_verified = True
                    if otp.sent_to_mobile:
                        user.mobile_verified = True
                    user.save(update_fields=["email_verified", "mobile_verified"])
                elif purpose in ["verify_mobile", "mobile_verification"]:
                    user.mobile_verified = True
                    user.save(update_fields=["mobile_verified"])

                otp.mark_verified()

                # Login user
                backends = get_backends()
                if backends:
                    user.backend = f"{backends[0].__module__}.{backends[0].__class__.__name__}"
                login(request, user)

                messages.success(request, "Verification successful.")
                request.session.pop("otp_user_id", None)
                request.session.pop("otp_purpose", None)
                return redirect("accounts:dashboard")
            messages.error(request, "Invalid or expired OTP.")
    else:
        form = OTPForm()
    return render(request, "accounts/verify_otp.html", {"form": form})


# ---------------- LOGOUT ----------------
def logout_view(request):
    logout(request)
    return redirect("accounts:login")


# ---------------- DASHBOARD ----------------
@login_required
def dashboard(request):
    profile = UserProfile.objects.filter(user=request.user).first()

    # Latest 5 parties & transactions (user-specific)
    latest_parties = Party.objects.filter(owner=request.user).order_by("-created_at")[:5]
    latest_txns = Transaction.objects.filter(party__owner=request.user).order_by("-date")[:5]

    # Totals (user-specific)
    total_credit = (
        Transaction.objects.filter(party__owner=request.user, txn_type="credit")
        .aggregate(Sum("amount"))["amount__sum"]
        or 0
    )
    total_debit = (
        Transaction.objects.filter(party__owner=request.user, txn_type="debit")
        .aggregate(Sum("amount"))["amount__sum"]
        or 0
    )

    balance = float(total_credit) - float(total_debit)

    # Plans (show all)
    plans = Plan.objects.all().order_by("price")

    context = {
        "profile": profile,
        "parties": latest_parties,        # 👈 latest parties
        "transactions": latest_txns,      # 👈 latest transactions
        "total_credit": total_credit,
        "total_debit": total_debit,
        "balance": balance,
        "plans": plans,
        "can_add_party": request.user.has_perm("khataapp.add_party"),
        "can_add_transaction": request.user.has_perm("khataapp.add_transaction"),
    }
    return render(request, "accounts/dashboard.html", context)

# ---------------- PLAN MANAGEMENT ----------------
@login_required
def subscribe_plan(request, plan_id):
    plan = get_object_or_404(Plan, id=plan_id)
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if plan.is_free:
        profile.plan = plan
        profile.save()
        messages.success(request, f"You are now subscribed to {plan.name}")
    else:
        messages.info(request, f"Paid plan. Please upgrade via payment.")
    return redirect("accounts:dashboard")


@login_required
def start_payment(request, plan_id):
    plan = get_object_or_404(Plan, id=plan_id)
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if plan.is_free:
        messages.info(request, f"{plan.name} is free. Switching...")
        return redirect("accounts:subscribe_plan", plan_id=plan.id)

    # Placeholder: simulate payment success
    return redirect("accounts:payment_success", plan_id=plan.id)


@login_required
def payment_success(request, plan_id):
    plan = get_object_or_404(Plan, id=plan_id)
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    profile.plan = plan
    profile.save()
    messages.success(request, f"Payment successful! You are now subscribed to {plan.name}")
    return redirect("accounts:dashboard")

@login_required
def profile_view(request):
    user = request.user
    profile, created = UserProfile.objects.get_or_create(user=user)

    # Party record link (admin side)
    party = Party.objects.filter(owner=user).first()

    if request.method == "POST":
        name = request.POST.get("name")
        mobile = request.POST.get("mobile")

        # Save to UserProfile
        profile.mobile = mobile
        profile.save()

        # Save to Party also (sync with admin khataapp)
        if party:
            party.name = name
            party.mobile = mobile
            party.save()

        return redirect("dashboard")

    context = {
        "profile": profile,
        "party": party,
    }
    return render(request, "accounts/complete_profile.html", context)

@login_required
def dashboard_view(request):
    return render(request, "accounts/dashboard.html")

# accounts/views.py
@login_required
def activate_basic(request):
    profile = UserProfile.objects.get(user=request.user)
    profile.plan = "basic"
    profile.save()
    return redirect("dashboard")

