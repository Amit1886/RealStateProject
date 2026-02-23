from django.urls import path

from . import views

app_name = "demo_center"

urlpatterns = [
    path("", views.index, name="index"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("user-experience/", views.user_experience, name="user_experience"),
    path("user-demo/", views.user_demo, name="user_demo"),
    path("marketing-ads/", views.marketing_ads, name="marketing_ads"),
    path("courier-transport/", views.courier_transport, name="courier_transport"),
    path("accounting/", views.accounting, name="accounting"),
    path("hr/", views.hr, name="hr"),
    path("autopilot-logs/", views.autopilot_logs, name="autopilot_logs"),
    path("how-it-works/", views.how_it_works, name="how_it_works"),
    path("reset/", views.reset_and_redirect, name="reset"),
    # APIs
    path("api/state/", views.api_state, name="api_state"),
    path("api/user-state/", views.api_user_state, name="api_user_state"),
    path("api/reset/", views.api_reset, name="api_reset"),
    path("api/toggle/<str:key>/", views.api_toggle, name="api_toggle"),
]
