from django.urls import path
from . import views

app_name = "core_settings"

urlpatterns = [
    path("", views.settings_dashboard, name="dashboard"),
    path("center/", views.settings_center, name="settings_center"),
    path("permissions/", views.user_permissions_view, name="user_permissions"),
    path("plans/", views.plan_permissions_view, name="plan_permissions"),
    path("user-overrides/", views.user_feature_overrides_view, name="user_feature_overrides"),
    path("api/settings/all/", views.api_settings_all, name="api_settings_all"),
    path("api/settings/update/", views.api_settings_update, name="api_settings_update"),
    path("settings/", views.settings_view, name="site_settings")
]
