from django.urls import path
from . import views

app_name = "core_settings"

urlpatterns = [
    path("", views.settings_dashboard, name="dashboard"),
    path("permissions/", views.user_permissions_view, name="user_permissions"),
    path("plans/", views.plan_permissions_view, name="plan_permissions"),
]
