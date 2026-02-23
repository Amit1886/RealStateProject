from django.contrib import admin

from .models import (
    PrintRenderLog,
    PrintTemplate,
    PrinterConfig,
    PrinterTestLog,
    TemplatePlanAccess,
    UserPrintTemplate,
)


@admin.register(PrinterConfig)
class PrinterConfigAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "model_name", "printer_type", "connection_type", "auto_print", "is_default", "updated_at")
    list_filter = ("printer_type", "connection_type", "auto_print", "is_default")
    search_fields = ("user__email", "user__username", "model_name")


@admin.register(PrinterTestLog)
class PrinterTestLogAdmin(admin.ModelAdmin):
    list_display = ("id", "printer", "result", "message", "created_at")
    list_filter = ("result", "created_at")
    search_fields = ("printer__model_name", "printer__user__email", "message")
    readonly_fields = ("printer", "result", "message", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class TemplatePlanAccessInline(admin.TabularInline):
    model = TemplatePlanAccess
    extra = 0


@admin.register(PrintTemplate)
class PrintTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "document_type",
        "paper_size",
        "is_default",
        "is_active",
        "is_admin_approved",
        "restrict_basic_plan",
        "updated_at",
    )
    list_filter = ("document_type", "paper_size", "is_active", "is_admin_approved", "restrict_basic_plan", "admin_only")
    search_fields = ("name", "slug", "description")
    readonly_fields = ("created_by", "approved_by", "created_at", "updated_at")
    inlines = [TemplatePlanAccessInline]


@admin.register(TemplatePlanAccess)
class TemplatePlanAccessAdmin(admin.ModelAdmin):
    list_display = ("id", "template", "plan", "is_enabled", "is_default_for_plan", "allow_advanced_fields", "updated_at")
    list_filter = ("is_enabled", "is_default_for_plan", "allow_advanced_fields")
    search_fields = ("template__name", "plan__name")


@admin.register(UserPrintTemplate)
class UserPrintTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "name",
        "document_type",
        "print_mode",
        "paper_size",
        "is_default",
        "is_active",
        "updated_at",
    )
    list_filter = ("document_type", "print_mode", "paper_size", "is_default", "is_active", "theme_mode")
    search_fields = ("user__email", "user__username", "name")


@admin.register(PrintRenderLog)
class PrintRenderLogAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "document_type", "print_mode", "status", "source_model", "source_id", "created_at")
    list_filter = ("document_type", "print_mode", "status", "paper_size", "created_at")
    search_fields = ("user__email", "source_model", "source_id", "error_message")
    readonly_fields = (
        "user",
        "template",
        "user_template",
        "source_model",
        "source_id",
        "document_type",
        "print_mode",
        "paper_size",
        "status",
        "error_message",
        "payload",
        "rendered_html",
        "rendered_css",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
