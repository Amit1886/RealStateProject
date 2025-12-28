from django.contrib import admin
from .models import UISettings, CompanySettings, AppSettings, ModuleSettings, FeatureSettings, SaaSSettings

@admin.register(UISettings)
class UISettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("🎨 Colors", {
            "fields": ("primary_color","secondary_color","success_color","danger_color")
        }),
        ("🌙 Theme", {
            "fields": ("theme_mode",)
        }),
        ("📐 Layout", {
            "fields": ("sidebar_position","sidebar_collapsed")
        }),
        ("🧭 Navigation", {
            "fields": (
                "show_dashboard","show_party","show_transaction",
                "show_commerce","show_reports","show_settings"
            )
        }),
    )

    def has_add_permission(self, request):
        return not UISettings.objects.exists()


@admin.register(CompanySettings)
class CompanySettingsAdmin(admin.ModelAdmin):
    list_display = ("company_name", "mobile", "email")


@admin.register(AppSettings)
class AppSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("🏢 Company", {"fields": ("company_name", "currency_symbol", "financial_year_start")}),
        ("📊 Dashboard", {"fields": ("show_profit_loss", "show_daily_summary")}),
        ("👤 Users", {"fields": ("allow_user_signup", "allow_social_login")}),
        ("🔐 System", {"fields": ("maintenance_mode", "enable_chat", "enable_notifications")}),
    )

    def has_add_permission(self, request):
        return not AppSettings.objects.exists()

@admin.register(ModuleSettings)
class ModuleSettingsAdmin(admin.ModelAdmin):
    list_display = ("module", "enabled")
    list_editable = ("enabled",)

@admin.register(FeatureSettings)
class FeatureSettingsAdmin(admin.ModelAdmin):
    list_display = ("feature", "enabled")
    list_editable = ("enabled",)

@admin.register(SaaSSettings)
class SaaSSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("🏢 Core", {"fields": ("enable_multi_company","enable_multi_user")}),
        ("💳 Subscription", {"fields": ("enable_subscription","enable_trial","trial_days")}),
        ("🔐 Advanced", {"fields": ("enable_audit_logs","enable_api_access")}),
    )

    def has_add_permission(self, request):
        return not SaaSSettings.objects.exists()

