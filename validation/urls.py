from django.urls import path
from realstateproject.lazy_views import lazy_view

app_name = "validation"

urlpatterns = [
    path("", lazy_view("validation.views.smart_alerts_dashboard"), name="dashboard"),
    path("<int:alert_id>/<str:action>/", lazy_view("validation.views.smart_alert_action"), name="action"),
]
