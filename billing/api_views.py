from decimal import Decimal

from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from leads.models import Lead

from .invoice_engine import create_invoice_for_lead
from .models import GSTDetail, Invoice, InvoiceItem
from .serializers import GSTDetailSerializer, InvoiceItemSerializer, InvoiceSerializer


class ScopedUserMixin:
    def filter_queryset_for_user(self, queryset):
        user = self.request.user
        return queryset if user.is_staff else queryset.filter(user=user)


class InvoiceViewSet(ScopedUserMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.filter_queryset_for_user(Invoice.objects.select_related("payment_order", "gst_detail", "user").prefetch_related("items").order_by("-issued_at"))


class InvoiceItemViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InvoiceItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = InvoiceItem.objects.select_related("invoice").order_by("id")
        return queryset if self.request.user.is_staff else queryset.filter(invoice__user=self.request.user)


class GSTDetailViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = GSTDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = GSTDetail.objects.select_related("invoice").order_by("-invoice__issued_at")
        return queryset if self.request.user.is_staff else queryset.filter(invoice__user=self.request.user)


class InvoiceCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if not (user.is_superuser or user.is_staff or getattr(user, "role", "") in {"admin", "super_admin", "state_admin", "district_admin", "area_admin"}):
            return Response({"detail": "Only admins can create invoices."}, status=status.HTTP_403_FORBIDDEN)

        lead_id = request.data.get("lead_id")
        amount = request.data.get("amount")
        product_name = str(request.data.get("product_name") or "Lead Conversion Service").strip()
        gst_rate = request.data.get("gst_rate")
        if lead_id:
            lead = get_object_or_404(Lead.objects.select_related("assigned_to", "created_by", "assigned_agent"), pk=lead_id)
            invoice = create_invoice_for_lead(lead, actor=user, amount=amount, source_note=str(request.data.get("note") or "API invoice creation"))
            if invoice is None:
                return Response({"detail": "Lead invoice could not be generated."}, status=status.HTTP_400_BAD_REQUEST)
            return Response(InvoiceSerializer(invoice, context={"request": request}).data, status=status.HTTP_201_CREATED)

        invoice_user = request.data.get("user_id")
        if invoice_user:
            from django.contrib.auth import get_user_model

            invoice_user = get_object_or_404(get_user_model(), pk=invoice_user)
        else:
            invoice_user = user

        try:
            gross_amount = Decimal(str(amount or "0"))
        except Exception:
            return Response({"detail": "amount must be numeric"}, status=status.HTTP_400_BAD_REQUEST)
        if gross_amount <= 0:
            return Response({"detail": "amount must be greater than zero"}, status=status.HTTP_400_BAD_REQUEST)
        rate = Decimal(str(gst_rate or "18.00"))
        divisor = Decimal("1.00") + (rate / Decimal("100.00"))
        subtotal = (gross_amount / divisor).quantize(Decimal("0.01"))
        gst_total = gross_amount - subtotal
        cgst = (gst_total / Decimal("2")).quantize(Decimal("0.01"))
        sgst = gst_total - cgst
        invoice = Invoice.objects.create(
            user=invoice_user,
            source_type=Invoice.SourceType.SERVICE_PURCHASE,
            status=Invoice.Status.ISSUED,
            subtotal=subtotal,
            gst_rate=rate,
            cgst=cgst,
            sgst=sgst,
            igst=Decimal("0.00"),
            total_amount=gross_amount,
            billing_name=str(request.data.get("billing_name") or invoice_user.get_full_name() or invoice_user.username),
            billing_email=str(request.data.get("billing_email") or invoice_user.email or ""),
            billing_address=str(request.data.get("billing_address") or ""),
            metadata={"created_via": "api", "product_name": product_name, "gst_rate": str(rate)},
        )
        InvoiceItem.objects.create(
            invoice=invoice,
            description=product_name,
            quantity=1,
            unit_price=subtotal,
            taxable_amount=subtotal,
            gst_rate=rate,
            total_amount=gross_amount,
        )
        GSTDetail.objects.create(
            invoice=invoice,
            company_gstin="",
            customer_gstin="",
            place_of_supply=str(request.data.get("place_of_supply") or ""),
            hsn_sac=str(request.data.get("hsn_sac") or "998399"),
            is_interstate=False,
            cgst_rate=(rate / Decimal("2")).quantize(Decimal("0.01")),
            sgst_rate=(rate / Decimal("2")).quantize(Decimal("0.01")),
            igst_rate=Decimal("0.00"),
            notes=str(request.data.get("note") or "Manual invoice creation"),
        )
        return Response(InvoiceSerializer(invoice, context={"request": request}).data, status=status.HTTP_201_CREATED)
