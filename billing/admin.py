from django.contrib import admin
from .models import (
    Plan, BillingInvoice, Subscription, PaymentGateway,
    Commerce, Payment
)


# =========================
# 💳 PLAN ADMIN
# =========================
@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'active', 'created_at')
    list_filter = ('active',)
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


# =========================
# 🧾 INVOICE ADMIN
# =========================
@admin.register(BillingInvoice)
class BillingInvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "user", "plan", "amount", "status", "created_at")
    search_fields = ("invoice_number", "user__username")

# =========================
# 📦 SUBSCRIPTION ADMIN
# =========================
@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'status', 'start_date', 'end_date', 'created_at')
    list_filter = ('status', 'plan')
    search_fields = ('user__username', 'plan__name')


# =========================
# 🏦 PAYMENT GATEWAY ADMIN
# =========================
@admin.register(PaymentGateway)
class PaymentGatewayAdmin(admin.ModelAdmin):
    list_display = ('name', 'provider', 'active', 'created_at')
    list_filter = ('provider', 'active')
    search_fields = ('name',)


# =========================
# 🏪 COMMERCE ADMIN
# =========================
@admin.register(Commerce)
class CommerceAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'user', 'category', 'contact_number', 'created_at')
    search_fields = ('business_name', 'user__username', 'contact_number')
    list_filter = ('category',)


# =========================
# 💰 PAYMENT ADMIN
# =========================
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'amount', 'payment_method', 'payment_status', 'created_at')
    list_filter = ('payment_status', 'payment_method')
    search_fields = ('transaction_id', 'order__id')


