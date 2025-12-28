# full path: ~/myproject/khatapro/khataapp/views.py
from django.http import FileResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.timezone import now
from decimal import Decimal
from .utils.credit_report import generate_credit_report_pdf
from .forms import (
    UserProfileDashboardForm,
    UserProfilePlanForm,
    PartyForm,
    TransactionForm,
)
from .models import UserProfile, Party, CreditEntry, EMI, CreditSettings, Transaction
from django.contrib.auth.models import User
from commerce.models import SalesVoucher, Invoice
from django.utils import timezone


# ----------------- Dashboard (Profile + Settings) -----------------
@login_required
def account_dashboard(request):
    """User dashboard for editing profile."""
    profile = get_object_or_404(UserProfile, user=request.user)

    if request.method == "POST":
        form = UserProfileDashboardForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect("account_dashboard")
    else:
        form = UserProfileDashboardForm(instance=profile)

    return render(request, "khataapp/account_dashboard.html", {"form": form})


# ----------------- Credit Report Download -----------------
@login_required
def credit_report_view(request):
    buffer = generate_credit_report_pdf()
    return FileResponse(buffer, as_attachment=True, filename="credit_report.pdf")


# ----------------- Profile View -----------------
@login_required
def profile_view(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    return render(request, "profile_view.html", {"profile": profile})


def user_list(request):
    signup_users = User.objects.filter(is_staff=False)
    return render(request, "khataapp/user_list.html", {"users": signup_users})


# ----------------- Plan Update -----------------
@login_required
def update_plan(request):
    profile = get_object_or_404(UserProfile, user=request.user)

    if request.method == "POST":
        form = UserProfilePlanForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Your subscription plan has been updated.")
            return redirect("profile_view")
    else:
        form = UserProfilePlanForm(instance=profile)

    return render(request, "update_plan.html", {"form": form, "profile": profile})


# ----------------- Credits -----------------
@login_required
def my_credits(request):
    """Show logged-in user's credit entries and EMI schedule."""
    try:
        party = Party.objects.get(user=request.user)
    except Party.DoesNotExist:
        messages.error(request, "No party profile found.")
        return render(request, "khataapp/my_credits.html", {"entries": []})

    entries = CreditEntry.objects.filter(owner=request.user)
    EMI.objects.filter(owner=request.user)

    return render(
        request,
        "khataapp/my_credits.html",
        {
            "party": party,
            "entries": entries,
            "EMI": EMI,
            "credit_settings": CreditSettings.get_solo(),  # singleton settings
            "today": now().date(),
        },
    )


# ---------------- Add Party ----------------
@login_required
def add_party(request):
    if request.method == "POST":
        name = request.POST.get("name")
        mobile = request.POST.get("mobile")
        email = request.POST.get("email")
        gst = request.POST.get("gst")
        address = request.POST.get("address")
        party_type = request.POST.get("party_type")
        upi_id = request.POST.get("upi_id")
        bank_account_number = request.POST.get("bank_account_number")
        whatsapp_number = request.POST.get("whatsapp_number")
        sms_number = request.POST.get("sms_number")
        qr_code = request.FILES.get("qr_code")

        if not name or not party_type:
            messages.error(request, "⚠️ Name and Party Type are required.")
            return redirect("khataapp:add_party")

        Party.objects.create(
            name=name,
            mobile=mobile,
            email=email,
            gst=gst,
            address=address,
            party_type=party_type,
            upi_id=upi_id,
            bank_account_number=bank_account_number,
            whatsapp_number=whatsapp_number,
            sms_number=sms_number,
            qr_code=qr_code,
            owner=request.user,
        )

        messages.success(request, f"✅ Party '{name}' added successfully!")
        return redirect("khataapp:party_list")

    return render(request, "khataapp/add_party.html")


# ---------------- Party List (Search + Filter + Owner-wise) ----------------
@login_required
def party_list(request):
    query = request.GET.get("q")
    ptype = request.GET.get("type")

    parties = Party.objects.filter(owner=request.user)

    if query:
        parties = parties.filter(name__icontains=query)
    if ptype:
        parties = parties.filter(party_type=ptype)

    context = {"parties": parties.order_by("-created_at")}
    return render(request, "khataapp/party_list.html", context)


# ---------------- Edit Party ----------------
@login_required
def edit_party(request, party_id):
    party = get_object_or_404(Party, id=party_id, owner=request.user)

    if request.method == "POST":
        party.name = request.POST.get("name")
        party.mobile = request.POST.get("mobile")
        party.email = request.POST.get("email")
        party.gst = request.POST.get("gst")
        party.address = request.POST.get("address")
        party.party_type = request.POST.get("party_type")
        party.upi_id = request.POST.get("upi_id")
        party.bank_account_number = request.POST.get("bank_account_number")
        party.whatsapp_number = request.POST.get("whatsapp_number")
        party.sms_number = request.POST.get("sms_number")

        if request.FILES.get("qr_code"):
            party.qr_code = request.FILES.get("qr_code")

        party.save()
        messages.success(request, "✅ Party updated successfully!")
        return redirect("khataapp:party_list")

    return render(request, "khataapp/edit_party.html", {"party": party})


# ---------------- View Party ----------------
@login_required
def party_view(request, party_id):
    party = get_object_or_404(Party, id=party_id)
    return render(request, "khataapp/party_view.html", {"party": party})


# ---------------- Delete Party ----------------
@login_required
def delete_party(request, party_id):
    party = get_object_or_404(Party, id=party_id, owner=request.user)
    party.delete()
    messages.success(request, "🗑️ Party deleted successfully!")
    return redirect("khataapp:party_list")

@login_required
def add_transaction(request):
    parties = Party.objects.filter(owner=request.user).order_by("name")
    vouchers = SalesVoucher.objects.filter(party__owner=request.user)
    invoices = Invoice.objects.filter(order__party__owner=request.user)

    if request.method == "POST":

        # Get basic fields
        party_id = request.POST.get("party")
        txn_type = request.POST.get("txn_type")
        txn_mode = request.POST.get("txn_mode")  # NEW FIELD
        amount = request.POST.get("amount")
        notes = request.POST.get("notes")
        date = request.POST.get("date") or timezone.now().date()

        # Optional fields
        voucher_id = request.POST.get("voucher")
        invoice_id = request.POST.get("invoice")
        gst_type = request.POST.get("gst_type") or None
        receipt_file = request.FILES.get("receipt")

        # Validate & convert amount
        try:
            amount = Decimal(amount)
        except:
            messages.error(request, "Invalid amount entered.")
            return redirect("khataapp:add_transaction")

        # Validate party belongs to current user
        party = get_object_or_404(Party, id=party_id, owner=request.user)

        # Create transaction
        Transaction.objects.create(
            party=party,
            txn_type=txn_type,
            txn_mode=txn_mode,
            amount=amount,
            notes=notes,
            date=date,
            receipt=receipt_file,
            voucher_id=voucher_id if voucher_id else None,
            invoice_id=invoice_id if invoice_id else None,
            gst_type=gst_type,
        )

        messages.success(request, "Transaction saved successfully.")

        # Redirect to transaction list
        return redirect("khataapp:transaction_list")

    return render(
        request,
        "khataapp/add_transaction.html",
        {
            "parties": parties,
            "vouchers": vouchers,
            "invoices": invoices,
        }
    )

@login_required
def transaction_list(request):
    transactions = Transaction.objects.filter(party__owner=request.user).order_by('-date')
    return render(request, 'khataapp/transaction_list.html', {'transactions': transactions})


@login_required
def transaction_view(request, id):
    txn = get_object_or_404(Transaction, id=id)
    return render(request, 'khataapp/transaction_view.html', {'txn': txn})


@login_required
def transaction_edit(request, id):
    txn = get_object_or_404(Transaction, id=id)

    if request.method == "POST":
        txn.party_id = request.POST.get("party")
        txn.txn_type = request.POST.get("txn_type")
        txn.amount = request.POST.get("amount")
        txn.date = request.POST.get("date")
        txn.notes = request.POST.get("notes")
        txn.save()

        messages.success(request, "Transaction updated successfully")
        return redirect("khataapp:transaction_view", id=txn.id)

    return render(request, "khataapp/transaction_edit.html", {
        "txn": txn,
        "parties": txn.party.__class__.objects.all()
    })


@login_required
def transaction_delete(request, id):
    txn = get_object_or_404(Transaction, id=id)

    txn.delete()
    messages.success(request, "Transaction deleted successfully")

    return redirect("khataapp:transaction_list")