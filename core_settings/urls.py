from django.urls import path
from realstateproject.lazy_views import lazy_view

app_name = "core_settings"

urlpatterns = [
    path("", lazy_view("core_settings.views.settings_dashboard"), name="dashboard"),
    path("center/", lazy_view("core_settings.views.settings_center"), name="settings_center"),
    path("feature-controls/", lazy_view("core_settings.views.feature_control_tower"), name="feature_control_tower"),
    path("system-mode/", lazy_view("system_mode.views.system_mode_panel"), name="system_mode_panel"),
    path("permissions/", lazy_view("core_settings.views.user_permissions_view"), name="user_permissions"),
    path("plans/", lazy_view("core_settings.views.plan_permissions_view"), name="plan_permissions"),
    path("user-overrides/", lazy_view("core_settings.views.user_feature_overrides_view"), name="user_feature_overrides"),
    path("api/settings/all/", lazy_view("core_settings.views.api_settings_all"), name="api_settings_all"),
    path("api/settings/update/", lazy_view("core_settings.views.api_settings_update"), name="api_settings_update"),
]
