# ~/myproject/khatapro/billing/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Plan, Subscription, Invoice, PaymentGateway


@login_required
def payment_success(request, plan_id):
    plan = get_object_or_404(Plan, id=plan_id)
    profile = request.user.userprofile
    profile.plan = plan
    profile.save()
    return redirect("dashboard")

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
                return redirect("profile_view")  # apne profile view ke name se replace karo
            except Plan.DoesNotExist:
                pass

    return render(request, "billing/choose_plan.html", {"plans": plans})


@login_required
def start_payment(request, plan_slug):
    """
    Start a payment:
    - If free plan → immediately activate subscription
    - If paid plan → create invoice + subscription (pending) and redirect to checkout
    """
    plan = get_object_or_404(Plan, slug=plan_slug)

    # Free plan: directly activate
    if plan.is_free or plan.price == 0:
        invoice = Invoice.objects.create(
            user=request.user,
            plan=plan,
            amount=0,
            paid=True
        )
        Subscription.objects.create(
            user=request.user,
            plan=plan,
            invoice=invoice,
            status="active",
            start_date=timezone.now()
        )
        for g in plan.groups.all():
            request.user.groups.add(g)
        messages.success(request, f"'{plan.name}' plan activated (Free).")
        return redirect("billing:dashboard")

    # Paid plan
    invoice = Invoice.objects.create(
        user=request.user,
        plan=plan,
        amount=plan.price,
        paid=False
    )
    subscription = Subscription.objects.create(
        user=request.user,
        plan=plan,
        invoice=invoice,
        status="pending",
        start_date=timezone.now()
    )

    # Pick gateway
    gateway = PaymentGateway.objects.filter(active=True).first()
    if not gateway:
        return render(request, "billing/no_gateway_configured.html", {"plan": plan})

    # Razorpay integration
    if gateway.provider == "razorpay":
        try:
            import razorpay
            client = razorpay.Client(auth=(gateway.api_key, gateway.api_secret))
            order_amount = int(plan.price * 100)  # in paise
            order_currency = "INR"
            order_receipt = f"inv_{invoice.id}"
            razor_order = client.order.create(dict(
                amount=order_amount,
                currency=order_currency,
                receipt=order_receipt,
                payment_capture=1
            ))
            invoice.payment_reference = razor_order.get("id")
            invoice.save(update_fields=["payment_reference"])
            return render(request, "billing/razorpay_checkout.html", {
                "gateway": gateway,
                "plan": plan,
                "invoice": invoice,
                "razor_order": razor_order,
                "razor_key": gateway.api_key,
                "subscription": subscription,
            })
        except Exception:
            return render(request, "billing/dummy_payment_form.html", {
                "gateway": gateway,
                "plan": plan,
                "invoice": invoice,
                "subscription": subscription
            })

    # PhonePe integration (dummy placeholder for now)
    if gateway.provider == "phonepe":
        return render(request, "billing/dummy_payment_form.html", {
            "gateway": gateway,
            "plan": plan,
            "invoice": invoice,
            "subscription": subscription
        })

    # Default → Dummy
    return render(request, "billing/dummy_payment_form.html", {
        "gateway": gateway,
        "plan": plan,
        "invoice": invoice,
        "subscription": subscription
    })


@login_required
def payment_page(request, invoice_number):
    invoice = get_object_or_404(Invoice, number=invoice_number, user=request.user)
    if request.method == "POST":
        # Simulated payment success
        invoice.paid = True
        invoice.payment_method = "simulated"
        invoice.payment_reference = f"SIM-{invoice.number}"
        invoice.paid_at = timezone.now()
        invoice.save()

        # Activate subscription
        try:
            sub = invoice.subscription
            sub.activate()
        except Subscription.DoesNotExist:
            Subscription.objects.create(
                user=request.user,
                plan=invoice.plan,
                invoice=invoice,
                status="active",
                start_date=timezone.now()
            )

        messages.success(request, "Payment successful — subscription activated.")
        return redirect("billing:dashboard")

    return render(request, "billing/payment_page.html", {"invoice": invoice})


@login_required
def dashboard(request):
    plans = Plan.objects.filter(active=True).order_by("price")
    invoices = request.user.billing_invoices.all().order_by("-created_at")[:10]
    subscriptions = request.user.subscriptions.all().order_by("-created_at")[:5]
    return render(request, "billing/dashboard.html", {
        "plans": plans,
        "invoices": invoices,
        "subscriptions": subscriptions,
    })


@login_required
def payment_return(request):
    return render(request, "billing/payment_return.html", {})


@csrf_exempt
def gateway_webhook(request, provider):
    """
    Webhook endpoint for payment gateways.
    Supports: razorpay, phonepe, dummy
    """
    gateway = PaymentGateway.objects.filter(provider=provider, active=True).first()
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        payload = {}

    # Razorpay webhook
    if provider == "razorpay":
        payment_id = payload.get("payload", {}).get("payment", {}).get("entity", {}).get("id")
        order_id = payload.get("payload", {}).get("payment", {}).get("entity", {}).get("order_id")
        status = payload.get("event")

        invoice = Invoice.objects.filter(payment_reference=order_id).first()
        if invoice and "captured" in str(status).lower():
            invoice.paid = True
            invoice.payment_reference = payment_id
            invoice.save(update_fields=["paid", "payment_reference"])
            Subscription.objects.filter(invoice=invoice).update(status="active", start_date=timezone.now())
            return HttpResponse(status=200)
        return HttpResponse(status=400)

    # PhonePe webhook (dummy verification for now)
    if provider == "phonepe":
        invoice_number = payload.get("transactionId")
        status = payload.get("status")
        invoice = Invoice.objects.filter(number=invoice_number).first()
        if invoice and status == "SUCCESS":
            invoice.paid = True
            invoice.save(update_fields=["paid"])
            Subscription.objects.filter(invoice=invoice).update(status="active", start_date=timezone.now())
            return HttpResponse(status=200)
        return HttpResponse(status=400)

    # Dummy webhook
    if provider == "dummy":
        inv_id = payload.get("invoice_id")
        invoice = Invoice.objects.filter(id=inv_id).first()
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
