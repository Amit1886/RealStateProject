from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from khataapp.models import Party, Order, SupplierPayment
from khataapp.forms import SupplierPaymentForm
from khataapp.services.supplier_services import SupplierService

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

    return render(request, 'khataapp/add_supplier_payment.html', {'form': form})
