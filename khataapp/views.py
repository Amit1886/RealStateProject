from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
<<<<<<< HEAD
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
=======
from django.utils import timezone
from datetime import timedelta
from khataapp.models import Party, Order, SupplierPayment
from khataapp.forms import SupplierPaymentForm
from khataapp.services.supplier_services import SupplierService
>>>>>>> fc1dc1ed70d9c9c0a937d50fa66837bc7585d738

def submit_contact(request):
    if request.method == 'POST':
        # handle contact form
        return JsonResponse({"status": "success"})
    else:
        return JsonResponse({"status": "error", "message": "Invalid request"})

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

<<<<<<< HEAD
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

=======
    return render(request, 'khataapp/add_supplier_payment.html', {'form': form})
>>>>>>> fc1dc1ed70d9c9c0a937d50fa66837bc7585d738
