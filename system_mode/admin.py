from django.contrib import admin

from .models import SystemMode


@admin.register(SystemMode)
class SystemModeAdmin(admin.ModelAdmin):
    list_display = ("current_mode", "is_locked", "updated_by", "updated_at")
    readonly_fields = ("updated_at",)
    fieldsets = (
        (
            "Global Layout Mode",
            {
                "fields": (
                    "current_mode",
                    "is_locked",
                    "updated_by",
                    "updated_at",
                )
            },
        ),
    )

    def has_add_permission(self, request):
        return not SystemMode.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
