from django.contrib import admin

from .models import DailyCashSummary, PaymentOrder, PaymentTransaction


@admin.register(PaymentOrder)
class PaymentOrderAdmin(admin.ModelAdmin):
    list_display = ("reference_id", "user", "gateway", "purpose", "amount", "status", "created_at")
    list_filter = ("gateway", "purpose", "status")
    search_fields = ("reference_id", "provider_order_id", "provider_payment_id", "user__email", "user__mobile")
    readonly_fields = ("reference_id", "provider_order_id", "provider_payment_id", "signature", "created_at", "updated_at", "paid_at", "failed_at")


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ("reference_id", "user", "mode", "status", "amount", "credited_to_wallet", "created_at")
    list_filter = ("mode", "status", "credited_to_wallet")
    search_fields = ("reference_id", "external_ref", "payment_id", "gateway_order_id", "user__email")
    readonly_fields = ("reference_id", "created_at", "updated_at", "processed_at")


@admin.register(DailyCashSummary)
class DailyCashSummaryAdmin(admin.ModelAdmin):
    list_display = ("cashier", "business_date", "opening_cash", "cash_in", "cash_out", "closing_cash")
    list_filter = ("business_date",)
