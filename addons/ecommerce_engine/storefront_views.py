from __future__ import annotations

import os

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from addons.common.db import DB_EXCEPTIONS, db_unavailable
from addons.common.eventing import publish_event_safe
from addons.ecommerce_engine.models import StorefrontOrder
from addons.ecommerce_engine.permissions import HasStorefrontKey
from addons.ecommerce_engine.services import mark_payment_paid
from addons.ecommerce_engine.webhook_verification import env_bool, verify_razorpay_webhook, verify_stripe_webhook
from addons.ecommerce_engine.storefront_services import create_checkout_order, list_published_products, record_payment_and_mark_paid


class PublicProductListAPI(APIView):
    permission_classes = [HasStorefrontKey]

    def get(self, request):
        try:
            branch_code = request.query_params.get("branch_code", "default")
            rows = list_published_products(branch_code=branch_code)
            return Response(
                [
                    {
                        "sku": row.sku,
                        "product_name": row.product_name,
                        "price": row.price,
                        "available_stock": row.available_stock,
                    }
                    for row in rows
                ]
            )
        except DB_EXCEPTIONS:
            return db_unavailable()


class PublicCheckoutAPI(APIView):
    permission_classes = [HasStorefrontKey]

    def post(self, request):
        required = ["customer_name", "customer_phone", "items"]
        for key in required:
            if key not in request.data:
                return Response({"detail": f"{key} is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            order, meta = create_checkout_order(
                branch_code=request.data.get("branch_code", "default"),
                customer_name=request.data["customer_name"],
                customer_phone=request.data["customer_phone"],
                items=request.data.get("items") or [],
            )
            publish_event_safe(
                event_key="storefront_order_created",
                payload={"storefront_order_id": order.id, "order_number": order.order_number, "total_amount": str(order.total_amount)},
                branch_code=order.branch_code,
                source="ecommerce_engine",
            )
            return Response({"order_id": order.id, **meta}, status=status.HTTP_201_CREATED)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except DB_EXCEPTIONS:
            return db_unavailable()


class PublicOrderStatusAPI(APIView):
    permission_classes = [HasStorefrontKey]

    def get(self, request, order_number: str):
        try:
            order = StorefrontOrder.objects.filter(order_number=order_number).first()
            if not order:
                return Response({"detail": "order not found"}, status=status.HTTP_404_NOT_FOUND)
            return Response(
                {
                    "order_number": order.order_number,
                    "status": order.status,
                    "payment_status": order.payment_status,
                    "total_amount": order.total_amount,
                    "currency": order.currency,
                }
            )
        except DB_EXCEPTIONS:
            return db_unavailable()


class PublicPaymentCapturedWebhookAPI(APIView):
    """
    Minimal webhook endpoint (gateway-agnostic) for payment capture callbacks.

    Expected payload:
      - order_number
      - gateway (optional, default: razorpay)
      - payment_ref
    """

    permission_classes = [HasStorefrontKey]

    def post(self, request):
        try:
            raw_body = request.body or b""
            order_number = request.data.get("order_number")
            payment_ref = request.data.get("payment_ref")
            gateway = str(request.data.get("gateway", "razorpay")).strip().lower()
            if not order_number or not payment_ref:
                return Response({"detail": "order_number and payment_ref are required"}, status=status.HTTP_400_BAD_REQUEST)

            order = StorefrontOrder.objects.filter(order_number=order_number).first()
            if not order:
                return Response({"detail": "order not found"}, status=status.HTTP_404_NOT_FOUND)

            if order.payment_status == StorefrontOrder.PaymentStatus.PAID:
                return Response({"status": "already_paid"})

            verify_enabled = env_bool("STOREFRONT_PAYMENT_WEBHOOK_VERIFY", False)
            if verify_enabled:
                if gateway == "razorpay":
                    secret = os.getenv("RAZORPAY_WEBHOOK_SECRET", "").strip()
                    sig = (request.META.get("HTTP_X_RAZORPAY_SIGNATURE") or "").strip()
                    if not verify_razorpay_webhook(raw_body=raw_body, signature=sig, secret=secret):
                        return Response({"detail": "invalid razorpay signature"}, status=status.HTTP_400_BAD_REQUEST)
                elif gateway == "stripe":
                    secret = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
                    sig_header = (request.META.get("HTTP_STRIPE_SIGNATURE") or "").strip()
                    tol = int(os.getenv("STRIPE_WEBHOOK_TOLERANCE_SECONDS", "300"))
                    if not verify_stripe_webhook(raw_body=raw_body, stripe_signature_header=sig_header, secret=secret, tolerance_seconds=tol):
                        return Response({"detail": "invalid stripe signature"}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({"detail": "unknown gateway"}, status=status.HTTP_400_BAD_REQUEST)

            record_payment_and_mark_paid(order=order, gateway=gateway, payment_ref=payment_ref, raw_payload=request.data)
            mark_payment_paid(order, gateway=gateway, payment_ref=payment_ref)
            return Response({"status": "ok"})
        except DB_EXCEPTIONS:
            return db_unavailable()
