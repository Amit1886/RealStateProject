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
from billing.services import sync_feature_registry, get_active_subscription, upgrade_subscription
from billing.models import FeatureRegistry, PlanFeature, SubscriptionHistory
from django.views.decorators.http import require_POST

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
                        paid=True,
                        status="paid"
                    )
                    Subscription.objects.create(
                        user=request.user,
                        plan=plan,
                        invoice=invoice,
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

    invoice = BillingInvoice.objects.filter(
        user=request.user,
        plan=plan,
        status="unpaid",
    ).order_by("-created_at").first()
    if not invoice:
        invoice = BillingInvoice.objects.create(
            user=request.user,
            plan=plan,
            amount=plan.price_monthly or plan.price,
            status="unpaid",
        )

    if request.method == "POST":
        gateway_id = request.POST.get("gateway_id")
        gateway = PaymentGateway.objects.filter(id=gateway_id, active=True).first()
        if not gateway:
            messages.error(request, "Please select an active payment gateway.")
            return redirect(f"/billing/checkout/?plan_id={plan.id}")

        # Dummy flow (simulate success)
        if gateway.provider == "dummy":
            invoice.paid = True
            invoice.status = "paid"
            invoice.payment_reference = "dummy"
            invoice.save(update_fields=["paid", "status", "payment_reference"])
            upgrade_subscription(request.user, plan)
            return redirect("billing:payment-success", plan_id=plan.id)

        # Real gateway placeholder
        messages.info(request, f"Proceed to {gateway.name} payment. (Integration pending)")
        return redirect("billing:checkout")  # stay on page

    gateways = PaymentGateway.objects.filter(active=True)
    return render(request, "billing/checkout.html", {
        "plan": plan,
        "invoice": invoice,
        "gateways": gateways,
    })


# --------------------------------------------------------------------------------
# PAYMENT SUCCESS PAGE
# --------------------------------------------------------------------------------
@login_required
def payment_success(request, plan_id):
    plan = get_object_or_404(Plan, id=plan_id)
    upgrade_subscription(request.user, plan)
    latest_invoice = BillingInvoice.objects.filter(user=request.user, plan=plan).order_by("-created_at").first()
    return render(request, "billing/payment_success.html", {"plan": plan, "invoice": latest_invoice})


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
    subscriptions = request.user.billing_subscriptions.all().order_by("-created_at")[:5]

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
# USER PLAN MANAGEMENT (Profile -> Settings -> Plan Management)
# --------------------------------------------------------------------------------
@login_required
def plan_management(request):
    sync_feature_registry()
    plans = Plan.objects.filter(active=True).order_by("price_monthly", "price")
    subscription = get_active_subscription(request.user)
    current_plan = subscription.plan if subscription else None
    features = FeatureRegistry.objects.filter(active=True)
    plan_features = {}
    for plan in plans:
        plan_features[plan.id] = set(
            PlanFeature.objects.filter(plan=plan, enabled=True).values_list("feature_id", flat=True)
        )
    return render(request, "billing/plan_management.html", {
        "plans": plans,
        "current_plan": current_plan,
        "features": features,
        "plan_features": plan_features,
    })


@login_required
@require_POST
def start_upgrade(request, plan_id):
    plan = get_object_or_404(Plan, id=plan_id, active=True)
    invoice = BillingInvoice.objects.create(
        user=request.user,
        plan=plan,
        amount=plan.price_monthly or plan.price,
        status="unpaid",
    )
    SubscriptionHistory.objects.create(
        user=request.user,
        plan=plan,
        event_type="payment",
        details={"invoice_id": invoice.id, "source": "start_upgrade"},
    )
    return redirect(f"/billing/checkout/?plan_id={plan.id}")


# --------------------------------------------------------------------------------
# ADMIN FEATURE MATRIX
# --------------------------------------------------------------------------------
@login_required
def feature_matrix(request):
    if not request.user.is_staff and not request.user.is_superuser:
        return HttpResponse("Admin access required", status=403)
    sync_feature_registry()
    plans = Plan.objects.filter(active=True).order_by("price_monthly", "price")
    features = FeatureRegistry.objects.filter(active=True)
    matrix = {}
    for plan in plans:
        enabled = set(
            PlanFeature.objects.filter(plan=plan, enabled=True).values_list("feature_id", flat=True)
        )
        matrix[plan.id] = enabled
    return render(request, "billing/feature_matrix.html", {
        "plans": plans,
        "features": features,
        "matrix": matrix,
    })


@login_required
@require_POST
def feature_matrix_save(request):
    if not request.user.is_staff and not request.user.is_superuser:
        return HttpResponse("Admin access required", status=403)
    sync_feature_registry()
    payload = json.loads(request.body.decode("utf-8"))
    plan_id = payload.get("plan_id")
    feature_ids = payload.get("feature_ids", [])
    plan = get_object_or_404(Plan, id=plan_id)
    PlanFeature.objects.filter(plan=plan).exclude(feature_id__in=feature_ids).delete()
    for feature_id in feature_ids:
        PlanFeature.objects.update_or_create(
            plan=plan,
            feature_id=feature_id,
            defaults={"enabled": True},
        )
    return HttpResponse(status=204)


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


@login_required
def billing_history(request):
    invoices = BillingInvoice.objects.filter(user=request.user).order_by("-created_at")
    subscriptions = Subscription.objects.filter(user=request.user).order_by("-created_at")
    events = SubscriptionHistory.objects.filter(user=request.user).order_by("-created_at")[:50]
    return render(request, "billing/history.html", {
        "invoices": invoices,
        "subscriptions": subscriptions,
        "events": events,
    })
