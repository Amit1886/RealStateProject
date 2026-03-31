from django.contrib import admin

from voice.models import VoiceCall, VoiceCallTurn, VoiceCommand


@admin.register(VoiceCommand)
class VoiceCommandAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "parsed_intent", "status", "created_at")
    list_filter = ("status", "parsed_intent", "created_at")
    search_fields = ("raw_text", "error")
    readonly_fields = ("created_at",)
    ordering = ("-created_at", "-id")


@admin.register(VoiceCall)
class VoiceCallAdmin(admin.ModelAdmin):
    list_display = ("id", "lead", "agent", "status", "trigger", "qualified", "qualification_status", "provider", "created_at")
    list_filter = ("status", "trigger", "qualified", "qualification_status", "provider")
    search_fields = ("lead__name", "lead__mobile", "agent__email", "provider_call_id", "summary")
    readonly_fields = ("created_at", "updated_at", "started_at", "completed_at")
    ordering = ("-created_at", "-id")


@admin.register(VoiceCallTurn)
class VoiceCallTurnAdmin(admin.ModelAdmin):
    list_display = ("id", "call", "speaker", "sequence", "created_at")
    list_filter = ("speaker",)
    search_fields = ("message", "call__lead__name")
