from django.contrib import admin

from crm.models import (
    AgentAchievement,
    AgentScore,
    CallLog,
    CustomerNote,
    CustomerProfile,
    FollowUp,
    LocalShop,
    OverrideLog,
    UnitHold,
)


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "company", "lifecycle_stage", "last_contacted_at")


@admin.register(CustomerNote)
class CustomerNoteAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "author", "created_at")


@admin.register(CallLog)
class CallLogAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "lead", "agent", "direction", "duration_seconds", "missed_call", "created_at")
    list_filter = ("direction", "missed_call", "telephony_provider")
    search_fields = ("phone_number", "external_call_id", "lead__name", "customer__user__email")


@admin.register(FollowUp)
class FollowUpAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "owner", "title", "due_at", "completed_at")


@admin.register(LocalShop)
class LocalShopAdmin(admin.ModelAdmin):
    list_display = ("id", "shop_name", "mobile", "agent", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("shop_name", "mobile")


@admin.register(OverrideLog)
class OverrideLogAdmin(admin.ModelAdmin):
    list_display = ("id", "admin", "action_type", "target_model", "target_object_id", "reason", "timestamp")
    list_filter = ("action_type", "target_model", "timestamp")
    search_fields = ("target_model", "target_object_id", "reason")


@admin.register(UnitHold)
class UnitHoldAdmin(admin.ModelAdmin):
    list_display = ("id", "unit", "agent", "status", "hold_start", "hold_end", "released_at")
    list_filter = ("status", "hold_end")
    search_fields = ("unit__title", "agent__email", "agent__username", "reason")


@admin.register(AgentScore)
class AgentScoreAdmin(admin.ModelAdmin):
    list_display = ("id", "agent", "score_date", "points", "leads_assigned", "leads_closed", "response_time_seconds")
    list_filter = ("score_date",)
    search_fields = ("agent__name", "agent__phone")


@admin.register(AgentAchievement)
class AgentAchievementAdmin(admin.ModelAdmin):
    list_display = ("id", "agent", "code", "title", "kind", "points", "achieved_at")
    list_filter = ("kind", "achieved_at")
    search_fields = ("agent__name", "code", "title")
