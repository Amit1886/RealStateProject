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
from .forms import ContactForm
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
from .models import ContactMessage
from django.views.decorators.csrf import csrf_exempt
from khataapp.models import Party, SupplierPayment
from khataapp.forms import SupplierPaymentForm
from khataapp.services.supplier_services import SupplierService
from datetime import timedelta
from billing.services import user_has_feature
from django.contrib.auth import get_user_model
from .models import FieldAgent, LoginLink, OfflineMessage
from .forms import FieldAgentForm



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


def contact_submit(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            obj = form.save()

            # 1. Auto-select admin user to forward message
            admin_user = User.objects.filter(is_superuser=True).first()
            if admin_user:
                obj.assigned_to = admin_user
                obj.forwarded_to_admin = True
                obj.save()

                # 2. Email notification to admin
                send_mail(
                    subject="New Contact Inquiry",
                    message=f"""
New contact request received:

Name: {obj.name}
Mobile: {obj.mobile}
Email: {obj.email}
Message:
{obj.message}
""",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[admin_user.email],
                )

            # 3. Auto-reply email to Customer
            send_mail(
                subject="Thank you for contacting us",
                message="Thank you for contacting support. Our team will respond shortly.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[obj.email],
            )

            return render(request, "core/contact_form.html", {"form": form})

    else:
        form = ContactForm()

    return render(request, "core/contact_form.html", {"form": form})


@csrf_exempt
def submit_contact(request):
    if request.method == "POST":
        name = request.POST.get("name")
        mobile = request.POST.get("mobile")
        email = request.POST.get("email")
        message_text = request.POST.get("message")

        if not name or not mobile or not email or not message_text:
            return JsonResponse({"status": "error", "message": "Missing fields"})

        ContactMessage.objects.create(
            name=name,
            mobile=mobile,
            email=email,
            message=message_text
        )

        return JsonResponse({
            "status": "success",
            "message": "Your message has been received successfully."
        })

    return JsonResponse({"status": "error", "message": "Invalid request"})


# ---------------- Field Agent Management ----------------
def _owner_agent_access(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return False
    if not user_has_feature(request.user, "field.agents"):
        return False
    return True


@login_required
def field_agent_list(request):
    if not _owner_agent_access(request):
        return render(request, "khataapp/agent_locked.html")

    agents = FieldAgent.objects.filter(owner=request.user).select_related("user")
    return render(request, "khataapp/agent_list.html", {"agents": agents})


@login_required
def field_agent_create(request):
    if not _owner_agent_access(request):
        return render(request, "khataapp/agent_locked.html")

    if request.method == "POST":
        form = FieldAgentForm(request.POST, owner=request.user)
        if form.is_valid():
            agent = form.save(commit=False)
            agent.owner = request.user
            agent.save()
            form.save_m2m()
            messages.success(request, "Field agent created successfully.")
            return redirect("khataapp:field_agent_list")
    else:
        form = FieldAgentForm(owner=request.user)

    return render(request, "khataapp/agent_form.html", {"form": form, "mode": "create"})


@login_required
def field_agent_edit(request, agent_id):
    if not _owner_agent_access(request):
        return render(request, "khataapp/agent_locked.html")

    agent = get_object_or_404(FieldAgent, id=agent_id, owner=request.user)
    if request.method == "POST":
        form = FieldAgentForm(request.POST, instance=agent, owner=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Field agent updated successfully.")
            return redirect("khataapp:field_agent_list")
    else:
        form = FieldAgentForm(instance=agent, owner=request.user)

    return render(request, "khataapp/agent_form.html", {"form": form, "mode": "edit", "agent": agent})


@login_required
def field_agent_generate_link(request, agent_id):
    if not _owner_agent_access(request):
        return render(request, "khataapp/agent_locked.html")

    agent = get_object_or_404(FieldAgent, id=agent_id, owner=request.user)

    mobile = agent.mobile or agent.user.mobile
    if not mobile:
        messages.warning(request, "Agent mobile number is missing.")
        return redirect("khataapp:field_agent_list")

    link = LoginLink.objects.create(
        user=agent.user,
        purpose="dashboard",
        expires_at=timezone.now() + timedelta(days=7),
    )

    url = request.build_absolute_uri(
        reverse("accounts:login_link", args=[link.token])
    )
    message = f"Click here for more details 👉 {url}"

    OfflineMessage.objects.create(
        party=None,
        recipient_name=agent.user.get_full_name() or agent.user.email,
        recipient_mobile=mobile,
        message=message,
        channel="whatsapp",
        status="pending"
    )

    messages.success(request, "Agent login link queued.")
    return redirect("khataapp:field_agent_list")

# ---------------- Supplier Management Views ----------------
@login_required
def supplier_dashboard(request):
    """Supplier purchase and due management dashboard"""
    suppliers = SupplierService.get_supplier_summary(request.user)
    summary = SupplierService.get_dashboard_summary(request.user)
    alerts = SupplierService.get_payment_alerts(request.user)

    context = {
        'suppliers': suppliers,
        'summary': summary,
        'alerts': alerts,
    }
    return render(request, 'khataapp/supplier_dashboard.html', context)


@login_required
def supplier_detail(request, supplier_id):
    """Detailed view of a supplier's transactions and outstanding amounts"""
    supplier = get_object_or_404(Party, id=supplier_id, owner=request.user, party_type='supplier')

    # Get outstanding orders
    outstanding_orders = Order.objects.filter(
        party=supplier,
        order_type='PURCHASE',
        due_amount__gt=0
    ).order_by('payment_due_date')

    # Get payment history
    payments = SupplierPayment.objects.filter(
        supplier=supplier
    ).select_related('order').order_by('-payment_date')

    # Get supplier summary
    suppliers_data = SupplierService.get_supplier_summary(request.user)
    summary = next((s for s in suppliers_data if s['id'] == supplier.id), {})

    # Get ledger
    ledger = SupplierService.get_supplier_ledger(supplier)

    context = {
        'supplier': supplier,
        'outstanding_orders': outstanding_orders,
        'payments': payments,
        'summary': summary,
        'ledger': ledger,
        'today': timezone.now().date(),
        'due_soon_date': timezone.now().date() + timedelta(days=7),
    }
    return render(request, 'khataapp/supplier_detail.html', context)


@login_required
def add_supplier_payment(request):
    """Add payment to supplier for outstanding purchase"""
    if request.method == 'POST':
        form = SupplierPaymentForm(request.POST, user=request.user)
        if form.is_valid():
            order = form.cleaned_data['order']
            payment = SupplierService.process_supplier_payment(
                order=order,
                amount=form.cleaned_data['amount'],
                payment_mode=form.cleaned_data['payment_mode'],
                reference=form.cleaned_data.get('reference'),
                notes=form.cleaned_data.get('notes'),
                payment_date=form.cleaned_data.get('payment_date')
            )

            messages.success(request, f"Payment of ₹{payment.amount} added successfully!")
            return redirect('khataapp:supplier_detail', supplier_id=order.party.id)
    else:
        form = SupplierPaymentForm(user=request.user)

        # Pre-select supplier if provided in query params
        supplier_id = request.GET.get('supplier')
        if supplier_id:
            try:
                supplier = Party.objects.get(id=supplier_id, owner=request.user, party_type='supplier')
                # Filter orders for this supplier
                form.fields['order'].queryset = Order.objects.filter(
                    party=supplier,
                    order_type='PURCHASE',
                    due_amount__gt=0
                )
            except Party.DoesNotExist:
                pass

        # Pre-select order if provided in query params
        order_id = request.GET.get('order')
        if order_id:
            try:
                order = Order.objects.get(id=order_id, owner=request.user, order_type='PURCHASE')
                form.initial['order'] = order
            except Order.DoesNotExist:
                pass

    return render(request, 'khataapp/add_supplier_payment.html', {'form': form})

