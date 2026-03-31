from __future__ import annotations

import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from rest_framework import decorators, permissions, response, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from billing.invoice_engine import create_invoice_for_lead
from billing.models import Invoice
from billing.permissions import FeatureActionPermission, feature_required
from wallet.services import get_or_create_wallet

from .models import DailyCashSummary, PaymentOrder, PaymentTransaction
from .serializers import DailyCashSummarySerializer, PaymentOrderSerializer, PaymentTransactionSerializer
from .services.gateway import (
    available_gateways,
    build_checkout_context,
    complete_payment_order,
    create_payment_order,
    create_razorpay_order_placeholder,
    process_webhook_payload,
    simulate_payment_success,
)


def _scoped_orders(user):
    qs = PaymentOrder.objects.select_related("user", "wallet", "order").all()
    return qs if user.is_staff else qs.filter(user=user)


def _scoped_transactions(user):
    qs = PaymentTransaction.objects.select_related("payment_order", "order", "user").all()
    return qs if user.is_staff else qs.filter(user=user)


class PaymentOrderViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentOrderSerializer
    permission_classes = [permissions.IsAuthenticated, FeatureActionPermission]
    feature_key = "crm.wallet"

    def get_queryset(self):
        return _scoped_orders(self.request.user)

    def create(self, request, *args, **kwargs):
        wallet = get_or_create_wallet(request.user)
        payment_order = create_payment_order(
            user=request.user,
            wallet=wallet,
            amount=request.data.get("amount"),
            gateway=request.data.get("gateway") or PaymentOrder.Gateway.DUMMY,
            purpose=request.data.get("purpose") or PaymentOrder.Purpose.WALLET_TOPUP,
            callback_url=request.data.get("callback_url") or "",
            return_url=request.data.get("return_url") or "",
            metadata=request.data.get("metadata") or {},
        )
        serializer = self.get_serializer(payment_order)
        payload = serializer.data
        payload["checkout"] = build_checkout_context(payment_order, request=request)
        return response.Response(payload, status=status.HTTP_201_CREATED)

    @decorators.action(detail=True, methods=["post"])
    def simulate_success(self, request, pk=None):
        payment_order = get_object_or_404(self.get_queryset(), pk=pk)
        order, txn = simulate_payment_success(payment_order)
        return response.Response(
            {
                "order": PaymentOrderSerializer(order, context={"request": request}).data,
                "transaction": PaymentTransactionSerializer(txn, context={"request": request}).data,
            }
        )


class PaymentTransactionViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentTransactionSerializer
    permission_classes = [permissions.IsAuthenticated, FeatureActionPermission]
    feature_key = "crm.wallet"

    def get_queryset(self):
        return _scoped_transactions(self.request.user)

    @decorators.action(detail=False, methods=["post"])
    def razorpay_create(self, request):
        payload = create_razorpay_order_placeholder(request.data.get("amount"))
        return response.Response(payload)


class DailyCashSummaryViewSet(viewsets.ModelViewSet):
    queryset = DailyCashSummary.objects.select_related("cashier").all()
    serializer_class = DailyCashSummarySerializer
    permission_classes = [permissions.IsAuthenticated, FeatureActionPermission]
    feature_key = "crm.wallet"


class PaymentLinkAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if not (user.is_superuser or user.is_staff or getattr(user, "role", "") in {"admin", "super_admin", "state_admin", "district_admin", "area_admin"}):
            return Response({"detail": "Only admins can generate payment links."}, status=status.HTTP_403_FORBIDDEN)

        invoice_id = request.data.get("invoice_id")
        lead_id = request.data.get("lead_id")
        gateway = (request.data.get("gateway") or PaymentOrder.Gateway.RAZORPAY).lower()
        amount = request.data.get("amount")
        callback_url = request.data.get("callback_url") or ""
        return_url = request.data.get("return_url") or ""
        metadata = request.data.get("metadata") or {}

        invoice = None
        if invoice_id:
            invoice = get_object_or_404(Invoice.objects.select_related("payment_order", "lead", "user"), pk=invoice_id)
        elif lead_id:
            from leads.models import Lead

            lead = get_object_or_404(Lead.objects.select_related("created_by", "assigned_to", "assigned_agent"), pk=lead_id)
            invoice = create_invoice_for_lead(lead, actor=user, amount=amount, source_note="Payment link generation")
            if invoice is None:
                return Response({"detail": "Could not generate invoice for lead."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"detail": "invoice_id or lead_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        payment_order = create_payment_order(
            user=invoice.user,
            wallet=getattr(invoice.user, "wallet", None),
            amount=amount or invoice.total_amount,
            gateway=gateway,
            purpose=PaymentOrder.Purpose.PROPERTY_BOOKING if invoice.source_type == Invoice.SourceType.PROPERTY_BOOKING else PaymentOrder.Purpose.SERVICE,
            order=getattr(invoice, "order", None),
            callback_url=callback_url or request.build_absolute_uri(reverse("payments:webhook", args=[gateway])),
            return_url=return_url or request.build_absolute_uri(reverse("payments:order_detail", args=[str(invoice.payment_order.reference_id)]) if getattr(invoice, "payment_order_id", None) else reverse("payments:checkout")),
            metadata={**metadata, "invoice_id": invoice.id, "lead_id": getattr(invoice, "lead_id", None)},
        )
        serializer = PaymentOrderSerializer(payment_order, context={"request": request})
        checkout = build_checkout_context(payment_order, request=request)
        checkout["order"] = serializer.data
        return Response(
            {
                "invoice": invoice.invoice_number,
                "payment_order": serializer.data,
                "checkout": checkout,
            },
            status=status.HTTP_201_CREATED,
        )


@login_required
@feature_required("crm.wallet")
@require_http_methods(["GET", "POST"])
def checkout(request):
    selected_gateway = (request.POST.get("gateway") or request.GET.get("gateway") or PaymentOrder.Gateway.RAZORPAY).lower()
    selected_amount = request.POST.get("amount") or request.GET.get("amount") or ""
    wallet = get_or_create_wallet(request.user)
    recent_orders = list(_scoped_orders(request.user)[:8])

    if request.method == "POST":
        try:
            payment_order = create_payment_order(
                user=request.user,
                wallet=wallet,
                amount=selected_amount,
                gateway=selected_gateway,
                purpose=PaymentOrder.Purpose.WALLET_TOPUP,
                callback_url=request.build_absolute_uri("/").rstrip("/") + reverse("payments:webhook", args=[selected_gateway]),
                return_url=request.build_absolute_uri("/").rstrip("/") + reverse("payments:success", args=["00000000-0000-0000-0000-000000000000"]),
                metadata={"note": request.POST.get("note", ""), "source": "wallet_workspace"},
            )
        except ValueError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, f"{payment_order.get_gateway_display()} order created. Demo mode me simulate button use karke payment complete kar sakte ho.")
            return redirect("payments:order_detail", reference_id=payment_order.reference_id)

    context = {
        "wallet": wallet,
        "gateways": available_gateways(),
        "recent_orders": recent_orders,
        "selected_gateway": selected_gateway,
        "selected_amount": selected_amount,
    }
    return render(request, "payments/checkout.html", context)


@login_required
@feature_required("crm.wallet")
@require_GET
def payment_history(request):
    context = {
        "orders": _scoped_orders(request.user)[:20],
        "transactions": _scoped_transactions(request.user)[:20],
    }
    return render(request, "payments/history.html", context)


@login_required
@feature_required("crm.wallet")
@require_GET
def order_detail(request, reference_id):
    payment_order = get_object_or_404(_scoped_orders(request.user), reference_id=reference_id)
    try:
        invoice = payment_order.fintech_invoice
    except Exception:
        invoice = None
    context = {
        "payment_order": payment_order,
        "checkout": build_checkout_context(payment_order, request=request),
        "transactions": payment_order.transactions.order_by("-created_at"),
        "invoice": invoice,
    }
    return render(request, "payments/order_detail.html", context)


@login_required
@feature_required("crm.wallet")
@require_http_methods(["GET", "POST"])
def simulate_success_view(request, reference_id):
    payment_order = get_object_or_404(_scoped_orders(request.user), reference_id=reference_id)
    order, txn = simulate_payment_success(payment_order)
    messages.success(request, f"Demo payment successful. Wallet credited and invoice generated for {order.reference_id}.")
    return redirect("payments:success", reference_id=order.reference_id)


@login_required
@feature_required("crm.wallet")
@require_GET
def payment_success(request, reference_id):
    payment_order = get_object_or_404(_scoped_orders(request.user), reference_id=reference_id)
    try:
        invoice = payment_order.fintech_invoice
    except Exception:
        invoice = None
    return render(
        request,
        "payments/payment_success.html",
        {
            "payment_order": payment_order,
            "transactions": payment_order.transactions.order_by("-created_at"),
            "invoice": invoice,
        },
    )


@csrf_exempt
@require_POST
def webhook(request, gateway):
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON payload")

    order, txn = process_webhook_payload(
        gateway=gateway,
        body=request.body,
        headers=request.headers,
        parsed_payload=payload,
    )
    status_code = 200 if order else 404
    return JsonResponse(
        {
            "gateway": gateway,
            "order": str(order.reference_id) if order else "",
            "transaction": str(txn.reference_id) if txn else "",
            "status": order.status if order else "not_found",
        },
        status=status_code,
    )


@csrf_exempt
@require_POST
def webhook_any(request):
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON payload")
    gateway = (
        request.headers.get("X-Payment-Gateway")
        or payload.get("gateway")
        or payload.get("provider")
        or request.GET.get("gateway")
        or PaymentOrder.Gateway.DUMMY
    )
    order, txn = process_webhook_payload(
        gateway=gateway,
        body=request.body,
        headers=request.headers,
        parsed_payload=payload,
    )
    status_code = 200 if order else 404
    return JsonResponse(
        {
            "gateway": gateway,
            "order": str(order.reference_id) if order else "",
            "transaction": str(txn.reference_id) if txn else "",
            "status": order.status if order else "not_found",
        },
        status=status_code,
    )
