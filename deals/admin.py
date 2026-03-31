from django.contrib import admin

from .models import Deal, Payment


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ["id", "lead", "property", "agent", "deal_amount", "commission_amount", "status", "stage", "closing_date", "created_at"]
    list_filter = ["status", "stage", "created_at"]
    search_fields = ["lead__name", "agent__name", "property__title"]
    autocomplete_fields = ["lead", "property", "agent"]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["id", "deal", "payment_type", "direction", "amount", "adjusted_amount", "status", "agent", "approved_by", "paid_at"]
    list_filter = ["payment_type", "direction", "status", "created_at"]
    search_fields = ["deal__lead__name", "agent__name", "reference"]
