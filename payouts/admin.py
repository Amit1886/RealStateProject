from django.contrib import admin

from .models import Payout


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ["id", "agent", "lead", "amount", "status", "generated_at", "approved_at", "paid_at"]
    list_filter = ["status", "generated_at"]
    search_fields = ["id", "lead__name", "agent__name"]
    autocomplete_fields = ["agent", "lead", "generated_by", "approved_by"]
    readonly_fields = ["generated_at", "approved_at", "paid_at"]

