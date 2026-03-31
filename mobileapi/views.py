from __future__ import annotations

import os
from decimal import Decimal, InvalidOperation

from django.conf import settings
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import MobileCustomer
from .models import MobileInvoice
from .models import MobileInvoiceItem
from .models import MobilePayment
from .models import MobileProduct
from voice.services import start_voice_call
from voice.models import VoiceCall
from marketing.models import QRCode, Campaign
from crm.models import LocalShop
from django.contrib.auth import get_user_model


def _extract_token(auth_header: str | None) -> str:
    """
    Accepts:
    - Authorization: Token <token>
    - Authorization: <token>   (fallback)
    """
    if not auth_header:
        return ""
    auth_header = auth_header.strip()
    if auth_header.lower().startswith("token "):
        return auth_header[6:].strip()
    return auth_header


def _require_sync_token(request) -> Response | None:
    """
    Lightweight shared-token auth (same style as `commerce.api_sync.InvoiceSyncAPI`).

    Cloud server should set `SYNC_API_TOKEN` in environment.
    Mobile app sends `Authorization: Token <SYNC_API_TOKEN>`.
    """
    expected = (getattr(settings, "SYNC_API_TOKEN", "") or os.getenv("SYNC_API_TOKEN") or "").strip()
    auth = request.headers.get("Authorization") or request.META.get("HTTP_AUTHORIZATION")
    provided = _extract_token(auth)
    if not expected or provided != expected:
        return Response({"detail": "Unauthorized"}, status=401)
    return None


def _dt(value) -> timezone.datetime:
    if not value:
        return timezone.now()
    if isinstance(value, timezone.datetime):
        return value
    if isinstance(value, str):
        parsed = parse_datetime(value)
        if parsed is None:
            return timezone.now()
        if timezone.is_naive(parsed):
            return timezone.make_aware(parsed, timezone.get_current_timezone())
        return parsed
    return timezone.now()


def _dec(value) -> Decimal:
    try:
        if value is None:
            return Decimal("0")
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("0")

@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def app_home(request):
    return Response({
        "app": "JaisTech KhataBook",
        "status": "Live",
        "version": "1.0",
        "message": "Welcome to JaisTech Professional Mobile App"
    })



@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def login_api(request):
    user = authenticate(
        username=request.data.get('username'),
        password=request.data.get('password')
    )

    if user:
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        })

    return Response({'error': 'Invalid credentials'}, status=401)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def mobile_sync_push(request):
    """
    Offline-first push endpoint for the Flutter app.

    Request body (example):
    {
      "user_id": "<mobile-user-id>",
      "table": "customers",
      "rows": [ { ...sqlite row... }, ... ]
    }

    Auth:
    - Authorization: Token <SYNC_API_TOKEN>
    """
    unauthorized = _require_sync_token(request)
    if unauthorized is not None:
        return unauthorized

    table = (request.data.get("table") or "").strip()
    user_id = (request.data.get("user_id") or "").strip()
    rows = request.data.get("rows") or []

    if not user_id:
        return Response({"ok": False, "error": "Missing user_id"}, status=400)
    if table not in {"customers", "products", "invoices", "invoice_items", "payments"}:
        return Response({"ok": False, "error": f"Invalid table: {table}"}, status=400)
    if not isinstance(rows, list):
        return Response({"ok": False, "error": "rows must be a list"}, status=400)

    ids = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        rid = (r.get("id") or "").strip()
        if not rid:
            continue

        if table == "customers":
            MobileCustomer.objects.update_or_create(
                id=rid,
                defaults={
                    "user_id": user_id,
                    "name": (r.get("name") or "").strip(),
                    "phone": (r.get("phone") or "").strip(),
                    "address": (r.get("address") or "").strip(),
                    "created_at": _dt(r.get("created_at")),
                    "updated_at": _dt(r.get("updated_at")),
                    "is_synced": True,
                },
            )
        elif table == "products":
            MobileProduct.objects.update_or_create(
                id=rid,
                defaults={
                    "user_id": user_id,
                    "name": (r.get("name") or "").strip(),
                    "sku": (r.get("sku") or "").strip(),
                    "price": _dec(r.get("price")),
                    "tax_percent": _dec(r.get("tax_percent")),
                    "created_at": _dt(r.get("created_at")),
                    "updated_at": _dt(r.get("updated_at")),
                    "is_synced": True,
                },
            )
        elif table == "invoices":
            MobileInvoice.objects.update_or_create(
                id=rid,
                defaults={
                    "user_id": user_id,
                    "customer_id": (r.get("customer_id") or "").strip(),
                    "number": (r.get("number") or "").strip(),
                    "status": (r.get("status") or "unpaid").strip(),
                    "subtotal": _dec(r.get("subtotal")),
                    "discount": _dec(r.get("discount")),
                    "tax": _dec(r.get("tax")),
                    "total": _dec(r.get("total")),
                    "paid": _dec(r.get("paid")),
                    "balance": _dec(r.get("balance")),
                    "created_at": _dt(r.get("created_at")),
                    "updated_at": _dt(r.get("updated_at")),
                    "is_synced": True,
                },
            )
        elif table == "invoice_items":
            MobileInvoiceItem.objects.update_or_create(
                id=rid,
                defaults={
                    "invoice_id": (r.get("invoice_id") or "").strip(),
                    "product_id": (r.get("product_id") or "").strip(),
                    "name": (r.get("name") or "").strip(),
                    "qty": _dec(r.get("qty")),
                    "unit_price": _dec(r.get("unit_price")),
                    "tax_percent": _dec(r.get("tax_percent")),
                    "line_total": _dec(r.get("line_total")),
                    "created_at": _dt(r.get("created_at")),
                    "updated_at": _dt(r.get("updated_at")),
                    "is_synced": True,
                },
            )
        elif table == "payments":
            MobilePayment.objects.update_or_create(
                id=rid,
                defaults={
                    "invoice_id": (r.get("invoice_id") or "").strip(),
                    "amount": _dec(r.get("amount")),
                    "mode": (r.get("mode") or "cash").strip(),
                    "reference": (r.get("reference") or "").strip(),
                    "status": (r.get("status") or "success").strip(),
                    "paid_at": _dt(r.get("paid_at")),
                    "created_at": _dt(r.get("created_at")),
                    "updated_at": _dt(r.get("updated_at")),
                    "is_synced": True,
                },
            )

        ids.append(rid)

    return Response({"ok": True, "ids": ids})


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def mobile_sync_pull(request):
    """
    Offline-first pull endpoint for the Flutter app.

    Request body:
    {
      "user_id": "<mobile-user-id>",
      "since": "2026-01-01T00:00:00Z"   // optional
    }

    Response:
    { "ok": true, "data": { "customers": [...], "products": [...], ... } }
    """
    unauthorized = _require_sync_token(request)
    if unauthorized is not None:
        return unauthorized

    user_id = (request.data.get("user_id") or "").strip()
    if not user_id:
        return Response({"ok": False, "error": "Missing user_id"}, status=400)

    since = _dt(request.data.get("since")) if request.data.get("since") else None

    def _iso(dt):
        if not dt:
            return ""
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        return dt.isoformat()

    customers_qs = MobileCustomer.objects.filter(user_id=user_id)
    products_qs = MobileProduct.objects.filter(user_id=user_id)
    invoices_qs = MobileInvoice.objects.filter(user_id=user_id)

    if since is not None:
        customers_qs = customers_qs.filter(updated_at__gt=since)
        products_qs = products_qs.filter(updated_at__gt=since)
        invoices_qs = invoices_qs.filter(updated_at__gt=since)

    customers = [
        {
            "id": c.id,
            "user_id": c.user_id,
            "name": c.name,
            "phone": c.phone,
            "address": c.address,
            "created_at": _iso(c.created_at),
            "updated_at": _iso(c.updated_at),
            "is_synced": 1,
        }
        for c in customers_qs.order_by("updated_at")[:2000]
    ]

    products = [
        {
            "id": p.id,
            "user_id": p.user_id,
            "name": p.name,
            "sku": p.sku,
            "price": float(p.price),
            "tax_percent": float(p.tax_percent),
            "created_at": _iso(p.created_at),
            "updated_at": _iso(p.updated_at),
            "is_synced": 1,
        }
        for p in products_qs.order_by("updated_at")[:2000]
    ]

    invoices = [
        {
            "id": i.id,
            "user_id": i.user_id,
            "customer_id": i.customer_id,
            "number": i.number,
            "status": i.status,
            "subtotal": float(i.subtotal),
            "discount": float(i.discount),
            "tax": float(i.tax),
            "total": float(i.total),
            "paid": float(i.paid),
            "balance": float(i.balance),
            "created_at": _iso(i.created_at),
            "updated_at": _iso(i.updated_at),
            "is_synced": 1,
        }
        for i in invoices_qs.order_by("updated_at")[:2000]
    ]

    invoice_ids = [i["id"] for i in invoices] if invoices else list(invoices_qs.values_list("id", flat=True)[:2000])
    items_qs = MobileInvoiceItem.objects.filter(invoice_id__in=invoice_ids)
    payments_qs = MobilePayment.objects.filter(invoice_id__in=invoice_ids)

    if since is not None:
        items_qs = items_qs.filter(updated_at__gt=since)
        payments_qs = payments_qs.filter(updated_at__gt=since)

    invoice_items = [
        {
            "id": it.id,
            "invoice_id": it.invoice_id,
            "product_id": it.product_id,
            "name": it.name,
            "qty": float(it.qty),
            "unit_price": float(it.unit_price),
            "tax_percent": float(it.tax_percent),
            "line_total": float(it.line_total),
            "created_at": _iso(it.created_at),
            "updated_at": _iso(it.updated_at),
            "is_synced": 1,
        }
        for it in items_qs.order_by("updated_at")[:4000]
    ]

    payments = [
        {
            "id": p.id,
            "invoice_id": p.invoice_id,
            "amount": float(p.amount),
            "mode": p.mode,
            "reference": p.reference,
            "status": p.status,
            "paid_at": _iso(p.paid_at),
            "created_at": _iso(p.created_at),
            "updated_at": _iso(p.updated_at),
            "is_synced": 1,
        }
        for p in payments_qs.order_by("updated_at")[:4000]
    ]

    return Response(
        {
            "ok": True,
            "data": {
                "customers": customers,
                "products": products,
                "invoices": invoices,
                "invoice_items": invoice_items,
                "payments": payments,
            },
        }
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def api_start_ai_call(request):
    """
    Agent quick action: start AI voice call for a lead.
    """
    lead_id = request.data.get("lead_id")
    if not lead_id:
        return Response({"ok": False, "error": "lead_id required"}, status=400)
    try:
        from leads.models import Lead

        lead = Lead.objects.get(id=lead_id)
    except Exception:
        return Response({"ok": False, "error": "lead_not_found"}, status=404)

    call = start_voice_call(lead, trigger=VoiceCall.Trigger.MANUAL)
    return Response({"ok": True, "call_id": call.id, "status": call.status})


@api_view(["POST"])
@permission_classes([AllowAny])
def api_generate_qr(request):
    """
    Generate QR metadata for agent / campaign / product.
    Frontend can render QR from target_url.
    """
    kind = (request.data.get("kind") or QRCode.Kind.CAMPAIGN).strip()
    agent_id = request.data.get("agent_id")
    campaign_id = request.data.get("campaign_id")
    target_url = (request.data.get("target_url") or "").strip()

    agent = None
    if agent_id:
        User = get_user_model()
        agent = User.objects.filter(id=agent_id).first()

    campaign = Campaign.objects.filter(id=campaign_id).first() if campaign_id else None

    if not target_url:
        if campaign:
            target_url = request.build_absolute_uri(f"/ai-tools/whatsapp/mini/{campaign.id}/")
        elif agent:
            target_url = request.build_absolute_uri(f"/ref/{agent.id}/")

    qr = QRCode.objects.create(agent=agent, campaign=campaign, kind=kind, target_url=target_url)
    return Response({"ok": True, "qr_id": qr.id, "target_url": target_url, "kind": kind})


@api_view(["POST"])
@permission_classes([AllowAny])
def api_add_shop(request):
    """
    Local shop onboarding via agent.
    """
    shop_name = (request.data.get("shop_name") or "").strip()
    mobile = (request.data.get("mobile") or "").strip()
    if not shop_name or not mobile:
        return Response({"ok": False, "error": "shop_name and mobile required"}, status=400)

    User = get_user_model()
    agent = User.objects.filter(id=request.data.get("agent_id")).first()
    owner = agent or User.objects.filter(is_superuser=True).first()

    shop = LocalShop.objects.create(
        owner=owner,
        agent=agent,
        shop_name=shop_name,
        owner_name=(request.data.get("owner_name") or "").strip(),
        mobile=mobile,
        category=(request.data.get("category") or "").strip(),
        status=LocalShop.Status.NEW,
    )
    return Response({"ok": True, "shop_id": shop.id, "status": shop.status})
