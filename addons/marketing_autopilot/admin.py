from django.contrib import admin

from .models import AutoReplyRule, ContentSchedule, CreativeAsset, SocialAccountConnection


@admin.register(SocialAccountConnection)
class SocialAccountConnectionAdmin(admin.ModelAdmin):
    list_display = ("platform", "account_handle", "branch_code", "is_active")
    list_filter = ("platform", "is_active", "branch_code")


@admin.register(ContentSchedule)
class ContentScheduleAdmin(admin.ModelAdmin):
    list_display = ("title", "platform", "status", "scheduled_for", "branch_code")
    list_filter = ("platform", "status", "branch_code")


@admin.register(AutoReplyRule)
class AutoReplyRuleAdmin(admin.ModelAdmin):
    list_display = ("platform", "trigger_keyword", "is_active", "branch_code")
    list_filter = ("platform", "is_active")


@admin.register(CreativeAsset)
class CreativeAssetAdmin(admin.ModelAdmin):
    list_display = ("kind", "status", "branch_code", "created_at")
    list_filter = ("kind", "status", "branch_code")
