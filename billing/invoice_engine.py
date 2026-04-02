from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from core_settings.models import CompanySettings
from accounts.models import UserProfile

from .models import GSTDetail, Invoice, InvoiceItem


def _q(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value or "0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _default_company_settings() -> CompanySettings:
    company = CompanySettings.objects.order_by("id").first()
    if company:
        return company
    return CompanySettings.objects.create(
        company_name="Demo Realty Technologies",
        email=getattr(settings, "DEFAULT_FROM_EMAIL", "") or "billing@example.com",
        mobile="9999999999",
        address_line="Lucknow, Uttar Pradesh",
        gstin="09ABCDE1234F1Z5",
        state_code="09",
        invoice_prefix="INV",
        default_gst_rate=Decimal("18.00"),
    )


@transaction.atomic
def create_invoice_for_lead(lead, *, deal=None, actor=None, amount=None, source_note: str = ""):
    from leads.models import Lead as LeadModel

    if lead is None:
        return None
    lead = LeadModel.objects.select_related("company", "assigned_agent", "converted_customer", "interested_property").get(pk=lead.pk)
    if lead.billing_invoices.exists():
        existing = lead.billing_invoices.order_by("-created_at").first()
        if existing:
            return existing

    gross_amount = _q(amount or lead.deal_value or lead.budget or 0)
    if gross_amount <= Decimal("0.00"):
        return None

    company = _default_company_settings()
    gst_rate = _q(company.default_gst_rate or Decimal("18.00"))
    tax = _compute_tax_breakup(gross_amount=gross_amount, gst_rate=gst_rate, interstate=False)
    invoice_user = (
        getattr(getattr(lead, "converted_customer", None), "user", None)
        or getattr(lead, "created_by", None)
        or getattr(lead, "assigned_to", None)
        or actor
    )
    if invoice_user is None:
        from django.contrib.auth import get_user_model

        invoice_user = get_user_model().objects.order_by("id").first()
    if invoice_user is None:
        return None
    invoice = Invoice.objects.create(
        user=invoice_user,
        lead=lead,
        source_type=Invoice.SourceType.PROPERTY_BOOKING if lead.interested_property_id else Invoice.SourceType.SERVICE_PURCHASE,
        status=Invoice.Status.ISSUED,
        currency="INR",
        subtotal=tax["subtotal"],
        gst_rate=gst_rate,
        cgst=tax["cgst"],
        sgst=tax["sgst"],
        igst=tax["igst"],
        total_amount=gross_amount,
        billing_name=(
            getattr(getattr(lead, "converted_customer", None), "user", None) and getattr(getattr(lead.converted_customer, "user", None), "get_full_name", lambda: "")()
        )
        or lead.name
        or getattr(actor, "get_full_name", lambda: "")()
        or getattr(actor, "username", ""),
        billing_email=(
            getattr(getattr(lead, "converted_customer", None), "user", None) and getattr(getattr(lead.converted_customer, "user", None), "email", "")
        )
        or lead.email
        or getattr(actor, "email", "")
        or "",
        billing_address=(lead.metadata or {}).get("address", "") if isinstance(lead.metadata, dict) else "",
        company_name=company.company_name,
        company_gstin=company.gstin,
        company_address=company.full_address,
        issued_at=timezone.now(),
        metadata={
            "lead_id": lead.id,
            "deal_id": getattr(deal, "id", None),
            "source_note": source_note,
            "created_by": getattr(actor, "id", None),
        },
    )
    InvoiceItem.objects.create(
        invoice=invoice,
        description=lead.interested_property.title if getattr(lead, "interested_property_id", None) else "Lead conversion service",
        quantity=Decimal("1.00"),
        unit_price=tax["subtotal"],
        taxable_amount=tax["subtotal"],
        gst_rate=gst_rate,
        total_amount=gross_amount,
        metadata={"lead_id": lead.id, "deal_id": getattr(deal, "id", None)},
    )
    GSTDetail.objects.create(
        invoice=invoice,
        company_gstin=company.gstin,
        customer_gstin="",
        place_of_supply=getattr(lead, "state", "") or company.address_line or "Uttar Pradesh",
        hsn_sac="998399",
        is_interstate=False,
        cgst_rate=(gst_rate / Decimal("2")).quantize(Decimal("0.01")),
        sgst_rate=(gst_rate / Decimal("2")).quantize(Decimal("0.01")),
        igst_rate=Decimal("0.00"),
        notes=source_note or "Auto-generated lead conversion invoice",
    )
    return invoice


def _compute_tax_breakup(*, gross_amount: Decimal, gst_rate: Decimal, interstate: bool) -> dict:
    gross_amount = _q(gross_amount)
    gst_rate = _q(gst_rate)
    if gst_rate <= Decimal("0.00"):
        return {
            "subtotal": gross_amount,
            "gst_total": Decimal("0.00"),
            "cgst": Decimal("0.00"),
            "sgst": Decimal("0.00"),
            "igst": Decimal("0.00"),
        }
    divisor = Decimal("1.00") + (gst_rate / Decimal("100.00"))
    subtotal = (gross_amount / divisor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    gst_total = gross_amount - subtotal
    if interstate:
        igst = gst_total
        cgst = Decimal("0.00")
        sgst = Decimal("0.00")
    else:
        cgst = (gst_total / Decimal("2")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        sgst = gst_total - cgst
        igst = Decimal("0.00")
    return {
        "subtotal": subtotal,
        "gst_total": gst_total,
        "cgst": cgst,
        "sgst": sgst,
        "igst": igst,
    }


@transaction.atomic
def ensure_invoice_for_payment_order(payment_order):
    try:
        existing = payment_order.fintech_invoice
    except Invoice.DoesNotExist:
        existing = None
    if existing is not None:
        return existing

    company = _default_company_settings()
    profile = UserProfile.objects.filter(user=payment_order.user).first()
    place_of_supply = getattr(profile, "address", "") or company.address_line or "Uttar Pradesh"
    customer_gstin = (getattr(profile, "gst_number", "") or "").strip().upper()
    gst_rate = _q((payment_order.metadata or {}).get("gst_rate") or company.default_gst_rate or Decimal("18.00"))
    is_interstate = False
    if customer_gstin and company.state_code and not customer_gstin.startswith(company.state_code):
        is_interstate = True

    tax = _compute_tax_breakup(gross_amount=payment_order.amount, gst_rate=gst_rate, interstate=is_interstate)
    invoice = Invoice.objects.create(
        user=payment_order.user,
        payment_order=payment_order,
        source_type=Invoice.SourceType.WALLET_RECHARGE if payment_order.purpose == "wallet_topup" else Invoice.SourceType.MANUAL,
        status=Invoice.Status.PAID if payment_order.status == "paid" else Invoice.Status.ISSUED,
        currency=payment_order.currency,
        subtotal=tax["subtotal"],
        gst_rate=gst_rate,
        cgst=tax["cgst"],
        sgst=tax["sgst"],
        igst=tax["igst"],
        total_amount=_q(payment_order.amount),
        billing_name=getattr(profile, "full_name", "") or payment_order.user.get_full_name() or payment_order.user.username,
        billing_email=payment_order.user.email or "",
        billing_address=getattr(profile, "address", "") or "",
        company_name=company.company_name,
        company_gstin=company.gstin,
        company_address=company.full_address,
        issued_at=timezone.now(),
        paid_at=payment_order.paid_at,
        metadata={"payment_order": str(payment_order.reference_id), "gateway": payment_order.gateway},
    )
    InvoiceItem.objects.create(
        invoice=invoice,
        description="Wallet recharge",
        quantity=Decimal("1.00"),
        unit_price=tax["subtotal"],
        taxable_amount=tax["subtotal"],
        gst_rate=gst_rate,
        total_amount=_q(payment_order.amount),
        metadata={"purpose": payment_order.purpose},
    )
    GSTDetail.objects.create(
        invoice=invoice,
        company_gstin=company.gstin,
        customer_gstin=customer_gstin,
        place_of_supply=place_of_supply,
        hsn_sac="998399",
        is_interstate=is_interstate,
        cgst_rate=(gst_rate / Decimal("2")).quantize(Decimal("0.01")) if not is_interstate else Decimal("0.00"),
        sgst_rate=(gst_rate / Decimal("2")).quantize(Decimal("0.01")) if not is_interstate else Decimal("0.00"),
        igst_rate=gst_rate if is_interstate else Decimal("0.00"),
        notes=f"{payment_order.get_gateway_display()} recharge invoice",
    )

    if invoice.billing_email:
        try:
            send_mail(
                subject=f"Invoice {invoice.invoice_number}",
                message=f"Your payment of Rs {invoice.total_amount} is confirmed. Invoice: {invoice.invoice_number}",
                from_email=company.email or getattr(settings, "DEFAULT_FROM_EMAIL", None),
                recipient_list=[invoice.billing_email],
                fail_silently=True,
            )
        except Exception:
            pass

    return invoice
