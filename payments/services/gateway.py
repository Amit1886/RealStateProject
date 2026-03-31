from __future__ import annotations

import hashlib
import hmac
import json
import os
import uuid
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from payments.models import PaymentOrder, PaymentTransaction


def _quantize(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value or "0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _resolve_gateway_secret(gateway: str, *, field: str = "api_secret") -> str:
    from billing.models import PaymentGateway

    model = PaymentGateway.objects.filter(provider=gateway, active=True).order_by("-id").first()
    if model:
        value = getattr(model, field, "") or ""
        if value:
            return value

    env_map = {
        ("razorpay", "api_key"): "RAZORPAY_KEY_ID",
        ("razorpay", "api_secret"): "RAZORPAY_KEY_SECRET",
        ("razorpay", "webhook_secret"): "RAZORPAY_WEBHOOK_SECRET",
        ("stripe", "api_key"): "STRIPE_PUBLISHABLE_KEY",
        ("stripe", "api_secret"): "STRIPE_SECRET_KEY",
        ("stripe", "webhook_secret"): "STRIPE_WEBHOOK_SECRET",
    }
    env_key = env_map.get((gateway, field))
    return (os.getenv(env_key, "") if env_key else "") or ""


def available_gateways() -> list[dict]:
    from billing.models import PaymentGateway

    db_gateways = list(PaymentGateway.objects.filter(provider__in=["razorpay", "stripe", "dummy"]).order_by("-active", "name"))
    payload = []
    seen = set()
    for gateway in db_gateways:
        seen.add(gateway.provider)
        payload.append(
            {
                "provider": gateway.provider,
                "label": gateway.name or gateway.get_provider_display(),
                "active": gateway.active,
                "mode": "live" if gateway.active and _resolve_gateway_secret(gateway.provider, field="api_secret") else "demo",
            }
        )
    for provider, label in [("razorpay", "Razorpay"), ("stripe", "Stripe"), ("dummy", "Demo Gateway")]:
        if provider not in seen:
            payload.append({"provider": provider, "label": label, "active": provider == "dummy", "mode": "demo"})
    return payload


def create_payment_order(
    *,
    user,
    amount,
    gateway: str,
    purpose: str = PaymentOrder.Purpose.WALLET_TOPUP,
    wallet=None,
    order=None,
    callback_url: str = "",
    return_url: str = "",
    metadata: dict | None = None,
) -> PaymentOrder:
    amount = _quantize(amount)
    if amount <= Decimal("0.00"):
        raise ValueError("Amount must be greater than zero.")

    gateway = (gateway or PaymentOrder.Gateway.DUMMY).lower()
    if gateway not in {choice[0] for choice in PaymentOrder.Gateway.choices}:
        gateway = PaymentOrder.Gateway.DUMMY

    payment_order = PaymentOrder.objects.create(
        user=user,
        wallet=wallet,
        order=order,
        amount=amount,
        currency=getattr(wallet, "currency", None) or getattr(settings, "DEFAULT_CURRENCY", "INR"),
        gateway=gateway,
        purpose=purpose,
        status=PaymentOrder.Status.PENDING,
        callback_url=callback_url,
        return_url=return_url,
        metadata=metadata or {},
    )
    payment_order.provider_order_id = f"{gateway.upper()}_{str(payment_order.reference_id).replace('-', '')[:18]}"
    payment_order.save(update_fields=["provider_order_id", "updated_at"])
    return payment_order


def build_checkout_context(payment_order: PaymentOrder, *, request=None) -> dict:
    base_root = ""
    if request is not None:
        base_root = request.build_absolute_uri("/").rstrip("/")
    success_url = reverse("payments:simulate_success", args=[payment_order.reference_id])
    detail_url = reverse("payments:order_detail", args=[payment_order.reference_id])
    webhook_url = reverse("payments:webhook", args=[payment_order.gateway])
    return {
        "order": payment_order,
        "gateway_label": dict(PaymentOrder.Gateway.choices).get(payment_order.gateway, payment_order.gateway.title()),
        "gateway_mode": "live" if _resolve_gateway_secret(payment_order.gateway, field="api_secret") else "demo",
        "gateway_public_key": _resolve_gateway_secret(payment_order.gateway, field="api_key"),
        "provider_order_id": payment_order.provider_order_id,
        "checkout_reference": f"{base_root}{detail_url}" if base_root else detail_url,
        "webhook_url": f"{base_root}{webhook_url}" if base_root else webhook_url,
        "demo_success_url": f"{base_root}{success_url}" if base_root else success_url,
    }


def verify_razorpay_signature(*, order_id: str, payment_id: str, signature: str, secret: str) -> bool:
    if not all([order_id, payment_id, signature, secret]):
        return False
    body = f"{order_id}|{payment_id}".encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_stripe_signature(*, payload: bytes, signature_header: str, secret: str) -> bool:
    if not payload or not signature_header or not secret:
        return False
    parts = {}
    for chunk in signature_header.split(","):
        if "=" in chunk:
            key, value = chunk.split("=", 1)
            parts[key.strip()] = value.strip()
    timestamp = parts.get("t")
    received = parts.get("v1")
    if not timestamp or not received:
        return False
    signed_payload = f"{timestamp}.{payload.decode('utf-8')}".encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, received)


@transaction.atomic
def complete_payment_order(
    payment_order: PaymentOrder,
    *,
    payment_id: str,
    signature: str = "",
    payload: dict | None = None,
    mode: str | None = None,
    verified: bool = False,
) -> tuple[PaymentOrder, PaymentTransaction]:
    from billing.invoice_engine import ensure_invoice_for_payment_order
    from wallet.services import credit_wallet, get_or_create_wallet

    locked_order = PaymentOrder.objects.select_for_update().select_related("user", "wallet").get(pk=payment_order.pk)
    if locked_order.status == PaymentOrder.Status.PAID:
        existing = locked_order.transactions.order_by("-created_at").first()
        if existing:
            return locked_order, existing

    locked_order.status = PaymentOrder.Status.PAID
    locked_order.provider_payment_id = payment_id or locked_order.provider_payment_id
    locked_order.signature = signature or locked_order.signature
    locked_order.paid_at = timezone.now()
    order_meta = locked_order.metadata or {}
    order_meta["verified"] = bool(verified)
    locked_order.metadata = order_meta
    locked_order.save(update_fields=["status", "provider_payment_id", "signature", "paid_at", "metadata", "updated_at"])

    payment_txn, created = PaymentTransaction.objects.get_or_create(
        payment_order=locked_order,
        payment_id=payment_id or locked_order.provider_payment_id or str(uuid.uuid4()),
        defaults={
            "order": locked_order.order,
            "user": locked_order.user,
            "mode": mode or locked_order.gateway,
            "status": PaymentTransaction.Status.SUCCESS,
            "amount": locked_order.amount,
            "currency": locked_order.currency,
            "external_ref": locked_order.provider_order_id,
            "gateway_order_id": locked_order.provider_order_id,
            "signature": signature,
            "payload": payload or {},
            "processed_at": timezone.now(),
        },
    )
    if not created:
        payment_txn.status = PaymentTransaction.Status.SUCCESS
        payment_txn.mode = mode or payment_txn.mode or locked_order.gateway
        payment_txn.amount = locked_order.amount
        payment_txn.currency = locked_order.currency
        payment_txn.external_ref = locked_order.provider_order_id
        payment_txn.gateway_order_id = locked_order.provider_order_id
        payment_txn.signature = signature or payment_txn.signature
        payment_txn.payload = payload or payment_txn.payload
        payment_txn.processed_at = payment_txn.processed_at or timezone.now()
        payment_txn.save(
            update_fields=[
                "status",
                "mode",
                "amount",
                "currency",
                "external_ref",
                "gateway_order_id",
                "signature",
                "payload",
                "processed_at",
                "updated_at",
            ]
        )

    if locked_order.purpose == PaymentOrder.Purpose.WALLET_TOPUP and not payment_txn.credited_to_wallet:
        wallet = locked_order.wallet or get_or_create_wallet(locked_order.user)
        _, wallet_txn = credit_wallet(
            locked_order.user,
            locked_order.amount,
            source="add_money",
            reference=str(locked_order.reference_id),
            narration=f"{locked_order.get_gateway_display()} wallet top-up",
            actor=locked_order.user,
            metadata={"payment_order": str(locked_order.reference_id), "payment_id": payment_id},
        )
        payload = payment_txn.payload or {}
        payload["wallet_transaction_reference"] = str(wallet_txn.reference_id)
        payment_txn.payload = payload
        payment_txn.credited_to_wallet = True
        payment_txn.save(update_fields=["payload", "credited_to_wallet", "updated_at"])

    ensure_invoice_for_payment_order(locked_order)
    return locked_order, payment_txn


def mark_payment_failed(payment_order: PaymentOrder, *, reason: str = "", payload: dict | None = None) -> PaymentOrder:
    payment_order.status = PaymentOrder.Status.FAILED
    payment_order.failed_at = timezone.now()
    meta = payment_order.metadata or {}
    if reason:
        meta["failure_reason"] = reason
    if payload:
        meta["failure_payload"] = payload
    payment_order.metadata = meta
    payment_order.save(update_fields=["status", "failed_at", "metadata", "updated_at"])
    return payment_order


def simulate_payment_success(payment_order: PaymentOrder) -> tuple[PaymentOrder, PaymentTransaction]:
    payment_id = f"PAY_{str(payment_order.reference_id).replace('-', '')[:16]}"
    signature = ""
    if payment_order.gateway == PaymentOrder.Gateway.RAZORPAY:
        secret = _resolve_gateway_secret("razorpay", field="api_secret") or "demo_razorpay_secret"
        signature = hmac.new(
            secret.encode("utf-8"),
            f"{payment_order.provider_order_id}|{payment_id}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
    elif payment_order.gateway == PaymentOrder.Gateway.STRIPE:
        signature = "demo_stripe_signature"

    return complete_payment_order(
        payment_order,
        payment_id=payment_id,
        signature=signature,
        payload={"source": "demo_simulator", "gateway": payment_order.gateway},
        mode=payment_order.gateway,
        verified=True,
    )


def process_webhook_payload(*, gateway: str, body: bytes, headers: dict, parsed_payload: dict | None = None) -> tuple[PaymentOrder | None, PaymentTransaction | None]:
    payload = parsed_payload or {}
    gateway = (gateway or "").lower()

    if gateway == PaymentOrder.Gateway.RAZORPAY:
        entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        order_id = entity.get("order_id") or payload.get("order_id")
        payment_id = entity.get("id") or payload.get("payment_id")
        signature = headers.get("X-Razorpay-Signature", "")
        order_obj = PaymentOrder.objects.filter(provider_order_id=order_id).first()
        if not order_obj:
            return None, None
        secret = _resolve_gateway_secret("razorpay", field="webhook_secret") or _resolve_gateway_secret("razorpay", field="api_secret")
        verified = verify_razorpay_signature(order_id=order_id, payment_id=payment_id, signature=signature, secret=secret)
        if "captured" in json.dumps(payload).lower():
            return complete_payment_order(order_obj, payment_id=payment_id, signature=signature, payload=payload, mode="razorpay", verified=verified)
        mark_payment_failed(order_obj, reason="Webhook did not indicate capture", payload=payload)
        return order_obj, None

    if gateway == PaymentOrder.Gateway.STRIPE:
        signature = headers.get("Stripe-Signature", "")
        secret = _resolve_gateway_secret("stripe", field="webhook_secret")
        verified = verify_stripe_signature(payload=body, signature_header=signature, secret=secret) if secret else False
        data = payload.get("data", {}).get("object", {})
        order_id = data.get("metadata", {}).get("provider_order_id") or data.get("metadata", {}).get("payment_order_id")
        payment_id = data.get("id") or payload.get("id")
        order_obj = PaymentOrder.objects.filter(provider_order_id=order_id).first()
        if not order_obj:
            return None, None
        event_type = payload.get("type", "")
        if event_type == "payment_intent.succeeded":
            return complete_payment_order(order_obj, payment_id=payment_id, signature=signature, payload=payload, mode="stripe", verified=verified)
        mark_payment_failed(order_obj, reason=event_type or "Stripe payment failed", payload=payload)
        return order_obj, None

    reference = payload.get("reference_id") or payload.get("payment_order")
    order_obj = PaymentOrder.objects.filter(reference_id=reference).first() if reference else None
    if not order_obj:
        return None, None
    if str(payload.get("status", "")).lower() in {"paid", "success", "captured"}:
        return complete_payment_order(order_obj, payment_id=payload.get("payment_id") or f"DEMO_{order_obj.reference_id.hex[:14]}", payload=payload, mode="demo", verified=True)
    mark_payment_failed(order_obj, reason="Demo gateway marked failed", payload=payload)
    return order_obj, None


def create_razorpay_order_placeholder(amount):
    amount = _quantize(amount or "0.00")
    return {
        "gateway": "razorpay",
        "amount": amount,
        "amount_paise": int(amount * 100),
        "currency": "INR",
        "demo": True,
    }
