from django.urls import path
from .views import app_home
from .views import login_api
from .views import mobile_sync_pull
from .views import mobile_sync_push
from .views import api_start_ai_call, api_generate_qr, api_add_shop
from commerce import views as commerce_views

urlpatterns = [
    path("home/", app_home),
    path('login/', login_api),
    # Offline-first mobile sync (Flutter app)
    # Full URL: /api/v1/mobile/sync/push/ and /api/v1/mobile/sync/pull/
    path("v1/mobile/sync/push/", mobile_sync_push),
    path("v1/mobile/sync/pull/", mobile_sync_pull),
    path("ai/reorder-plan/", commerce_views.api_ai_reorder_plan),
    path("ai/reorder-plan/health", commerce_views.api_ai_reorder_plan_health),
    path("dashboard/reorder-summary/", commerce_views.api_dashboard_reorder_summary),
    path("dashboard/reorder-summary/health", commerce_views.api_dashboard_reorder_summary_health),
    path("ai/generate-po/", commerce_views.api_ai_generate_po),
    path("ai/voice-call/", api_start_ai_call),
    path("qr/generate/", api_generate_qr),
    path("shops/add/", api_add_shop),
    path("", app_home, name="api_home"),
]
