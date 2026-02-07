from django.urls import path
from .views import app_home
from .views import login_api
from commerce import views as commerce_views

urlpatterns = [
    path("home/", app_home),
    path('login/', login_api),
    path("ai/reorder-plan/", commerce_views.api_ai_reorder_plan),
    path("ai/reorder-plan/health", commerce_views.api_ai_reorder_plan_health),
    path("dashboard/reorder-summary/", commerce_views.api_dashboard_reorder_summary),
    path("dashboard/reorder-summary/health", commerce_views.api_dashboard_reorder_summary_health),
    path("ai/generate-po/", commerce_views.api_ai_generate_po),
    path("", app_home, name="api_home"),
]
