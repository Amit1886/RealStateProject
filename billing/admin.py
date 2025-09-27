# billing/admin.py
from django.contrib import admin
from .models import PaymentGateway, Plan, Subscription, Invoice

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "active", "created_at")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("groups",)

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "user", "plan", "amount", "paid", "created_at", "paid_at")
    list_filter = ("paid",)
    search_fields = ("number", "user__username")

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "status", "start_date", "created_at")
    list_filter = ("status", "plan")
    search_fields = ("user__username",)

@admin.register(PaymentGateway)
class PaymentGatewayAdmin(admin.ModelAdmin):
    list_display = ("name", "provider", "active", "created_at")
    list_editable = ("active",)
    search_fields = ("name", "provider")
