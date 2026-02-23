from django.urls import path

from .views import ChangeModeAPIView, CurrentModeAPIView, SystemModeAPIView


app_name = "system_mode"

urlpatterns = [
    path("system-mode/", SystemModeAPIView.as_view(), name="system_mode"),
    path("change-mode/", ChangeModeAPIView.as_view(), name="change_mode"),
    path("current-mode/", CurrentModeAPIView.as_view(), name="current_mode"),
]
