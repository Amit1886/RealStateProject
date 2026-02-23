from django.contrib import admin

from .models import (
    AutopilotAuditLog,
    AutopilotEvent,
    AutopilotExecution,
    AutopilotStepLog,
    BackupJob,
    FeatureToggle,
    WorkflowAction,
    WorkflowRule,
)


@admin.register(FeatureToggle)
class FeatureToggleAdmin(admin.ModelAdmin):
    list_display = ("key", "enabled", "updated_at")
    list_filter = ("enabled",)
    search_fields = ("key",)


class WorkflowActionInline(admin.TabularInline):
    model = WorkflowAction
    extra = 0


@admin.register(WorkflowRule)
class WorkflowRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "event_key", "is_active", "priority", "branch_code")
    list_filter = ("is_active", "event_key", "branch_code")
    search_fields = ("name", "event_key")
    inlines = [WorkflowActionInline]


@admin.register(AutopilotEvent)
class AutopilotEventAdmin(admin.ModelAdmin):
    list_display = ("event_key", "status", "attempts", "branch_code", "created_at")
    list_filter = ("status", "event_key", "branch_code")
    search_fields = ("event_key", "source")


@admin.register(AutopilotExecution)
class AutopilotExecutionAdmin(admin.ModelAdmin):
    list_display = ("event", "rule", "status", "created_at")
    list_filter = ("status",)


@admin.register(AutopilotStepLog)
class AutopilotStepLogAdmin(admin.ModelAdmin):
    list_display = ("execution", "action_key", "status", "attempt", "created_at")
    list_filter = ("status", "action_key")


@admin.register(AutopilotAuditLog)
class AutopilotAuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "target", "branch_code", "actor", "created_at")
    list_filter = ("action", "branch_code")


@admin.register(BackupJob)
class BackupJobAdmin(admin.ModelAdmin):
    list_display = ("storage", "snapshot_ref", "status", "created_at")
    list_filter = ("status", "storage")
