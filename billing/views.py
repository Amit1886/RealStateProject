from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json

# ✅ Import all models properly
from .models import (
    Plan, Subscription, BillingInvoice, PaymentGateway, Payment,
    Order, OrderItem, Warehouse, Stock, ChatMessage, ChatThread,
    Notification, PartyPortal
)
from .forms import CommerceForm   # if used later

from django.contrib.auth import authenticate, login

# --------------------------------------------------------------------------------
# CUSTOM LOGIN HANDLER (Role-Based Redirect)
# --------------------------------------------------------------------------------
def login_user(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(username=username, password=password)

        if user:
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            # ✅ Role-based redirect
            if user.is_superuser:
                return redirect("/admin/")  # Full admin
            elif user.is_staff:
                return redirect("billing:dashboard")  # Staff dashboard
            else:
                return redirect("billing:commerce_dashboard")  # Normal user dashboard
        else:
            messages.error(request, "Invalid credentials.")
            return redirect("login")

    return render(request, "billing/login.html")


# --------------------------------------------------------------------------------
# PLAN SELECTION
# --------------------------------------------------------------------------------
@login_required
def choose_plan(request):
    plans = Plan.objects.filter(active=True)

    if request.method == "POST":
        plan_id = request.POST.get("plan_id")
        if plan_id:
            try:
                plan = Plan.objects.get(id=plan_id)
                profile = request.user.userprofile
                profile.plan = plan
                profile.save()

                # ✅ Free plan → activate immediately
                if plan.is_free or plan.price == 0:
                    invoice = BillingInvoice.objects.create(
                        user=request.user,
                        plan=plan,
                        amount=0,
                        paid=True
                    )
                    Subscription.objects.create(
                        user=request.user,
                        plan=plan,
                        invoice=BillingInvoice,
                        status="active",
                        start_date=timezone.now()
                    )
                    messages.success(request, f"'{plan.name}' plan activated (Free).")
                    return redirect("billing:dashboard")
                else:
                    # ✅ Paid plan → go to checkout
                    return redirect(f"/billing/checkout/?plan_id={plan.id}")

            except Plan.DoesNotExist:
                messages.error(request, "Selected plan does not exist.")
                return redirect("billing:choose_plan")

    return render(request, "billing/choose_plan.html", {"plans": plans})


# --------------------------------------------------------------------------------
# CHECKOUT PAGE
# --------------------------------------------------------------------------------
@login_required
def checkout(request):
    plan_id = request.GET.get("plan_id")
    plan = get_object_or_404(Plan, id=plan_id)

    invoice, _ = BillingInvoice.objects.get_or_create(
        user=request.user,
        plan=plan,
        defaults={"amount": plan.price, "status": "unpaid"}
    )

    return render(request, "billing/checkout.html", {
        "plan": plan,
        "invoice": invoice
    })


# --------------------------------------------------------------------------------
# PAYMENT SUCCESS PAGE
# --------------------------------------------------------------------------------
@login_required
def payment_success(request, plan_id):
    plan = get_object_or_404(Plan, id=plan_id)
    return render(request, "billing/payment_success.html", {"plan": plan})


# --------------------------------------------------------------------------------
# BILLING DASHBOARD (Staff Access)
# --------------------------------------------------------------------------------
@login_required
def dashboard(request):
    """
    Dashboard visible to staff or admin users only.
    """
    user = request.user
    if not user.is_staff and not user.is_superuser:
        return redirect("billing:commerce_dashboard")

    plans = Plan.objects.filter(active=True).order_by("price")
    invoices = request.user.billing_invoices.all().order_by("-created_at")[:10]
    subscriptions = request.user.subscriptions.all().order_by("-created_at")[:5]

    return render(request, "billing/dashboard.html", {
        "plans": plans,
        "invoices": invoices,
        "subscriptions": subscriptions,
    })


# --------------------------------------------------------------------------------
# WEBHOOK HANDLERS (Razorpay, PhonePe, Dummy)
# --------------------------------------------------------------------------------
@csrf_exempt
def gateway_webhook(request, provider):
    gateway = PaymentGateway.objects.filter(provider=provider, active=True).first()
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        payload = {}

    # ✅ Razorpay
    if provider == "razorpay":
        payment_id = payload.get("payload", {}).get("payment", {}).get("entity", {}).get("id")
        order_id = payload.get("payload", {}).get("payment", {}).get("entity", {}).get("order_id")
        status = payload.get("event")

        invoice = BillingInvoice.objects.filter(payment_reference=order_id).first()
        if invoice and "captured" in str(status).lower():
            invoice.paid = True
            invoice.payment_reference = payment_id
            invoice.save(update_fields=["paid", "payment_reference"])
            Subscription.objects.filter(invoice=invoice).update(status="active", start_date=timezone.now())
            return HttpResponse(status=200)
        return HttpResponse(status=400)

    # ✅ PhonePe
    if provider == "phonepe":
        invoice_number = payload.get("transactionId")
        status = payload.get("status")
        invoice = BillingInvoice.objects.filter(number=invoice_number).first()
        if invoice and status == "SUCCESS":
            invoice.paid = True
            invoice.save(update_fields=["paid"])
            Subscription.objects.filter(invoice=invoice).update(status="active", start_date=timezone.now())
            return HttpResponse(status=200)
        return HttpResponse(status=400)

    # ✅ Dummy
    if provider == "dummy":
        inv_id = payload.get("invoice_id")
        invoice = BillingInvoice.objects.filter(id=inv_id).first()
        if not invoice:
            return HttpResponse(status=404)
        if payload.get("status") in ("paid", "success"):
            invoice.paid = True
            invoice.payment_reference = payload.get("payment_ref", "dummy")
            invoice.save(update_fields=["paid", "payment_reference"])
            Subscription.objects.filter(invoice=invoice).update(status="active", start_date=timezone.now())
        else:
            invoice.paid = False
            invoice.save(update_fields=["paid"])
            Subscription.objects.filter(invoice=invoice).update(status="cancelled")
        return HttpResponse(status=200)

    return HttpResponse(status=400)


# --------------------------------------------------------------------------------
# PLAN UPGRADE PAGE
# --------------------------------------------------------------------------------
@login_required
def upgrade_plan(request):
    user = request.user
    plans = Plan.objects.all().order_by("price")
    current_plan = getattr(getattr(user, "userprofile", None), "plan", None)

    return render(request, "billing/upgrade_plan.html", {
        "plans": plans,
        "current_plan": current_plan
    })


# --------------------------------------------------------------------------------
# COMMERCE DASHBOARD (Normal User Side)
# --------------------------------------------------------------------------------
@login_required
def commerce_dashboard(request):
    """
    Display commerce data if user's plan allows.
    Free plan → view-only mode
    Paid plan → full access
    """
    user = request.user
    profile = getattr(user, "userprofile", None)
    plan = getattr(profile, "plan", None)
    is_paid = plan and not plan.is_free

    context = {
        "is_paid": is_paid,
        "invoices": BillingInvoice.objects.filter(user=user),
        "payments": Payment.objects.filter(user=user),
        "orders": Order.objects.filter(user=user),
        "order_items": OrderItem.objects.all(),
        "warehouses": Warehouse.objects.all(),
        "stocks": Stock.objects.all(),
        "chats": ChatMessage.objects.filter(user=user),
        "threads": ChatThread.objects.filter(user=user),
        "notifications": Notification.objects.filter(user=user),
        "portals": PartyPortal.objects.filter(user=user),
    }

    return render(request, "billing/commerce_dashboard.html", context)
