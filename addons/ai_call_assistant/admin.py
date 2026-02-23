from django.contrib import admin

from addons.ai_call_assistant.models import CallLog, CallSession, IVRProviderConfig, WhatsAppFollowUp, WhatsAppProviderConfig


class CallLogInline(admin.TabularInline):
    model = CallLog
    extra = 0
    readonly_fields = ("event_type", "payload", "created_at")


@admin.register(CallSession)
class CallSessionAdmin(admin.ModelAdmin):
    list_display = ("caller_number", "status", "detected_intent", "branch_code", "created_at")
    list_filter = ("status", "detected_intent", "branch_code")
    search_fields = ("caller_number", "linked_order_ref")
    inlines = [CallLogInline]


@admin.register(WhatsAppFollowUp)
class WhatsAppFollowUpAdmin(admin.ModelAdmin):
    list_display = ("session", "status", "scheduled_for", "created_at")
    list_filter = ("status",)
    search_fields = ("session__caller_number", "provider_message_id")


@admin.register(WhatsAppProviderConfig)
class WhatsAppProviderConfigAdmin(admin.ModelAdmin):
    list_display = ("branch_code", "provider", "is_active", "sandbox", "updated_at")
    list_filter = ("provider", "is_active", "sandbox", "branch_code")
    search_fields = ("provider", "branch_code", "demo_sender")


@admin.register(IVRProviderConfig)
class IVRProviderConfigAdmin(admin.ModelAdmin):
    list_display = ("branch_code", "provider", "is_active", "sandbox", "updated_at")
    list_filter = ("provider", "is_active", "sandbox", "branch_code")
    search_fields = ("provider", "branch_code", "demo_number")

