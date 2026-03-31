from django.urls import path
from realstateproject.lazy_views import lazy_view

app_name = "whatsapp"

urlpatterns = [
    path("", lazy_view("whatsapp.control_views.whatsapp_control_center"), name="control_center"),
    # Modern dashboard (simplified UI)
    path("dashboard/", lazy_view("whatsapp.views.whatsapp_accounting_dashboard"), name="dashboard"),
    path("accounting/", lazy_view("whatsapp.views.whatsapp_accounting_dashboard"), name="accounting_dashboard"),
    path("setup/", lazy_view("whatsapp.setup_views.whatsapp_setup_wizard"), name="setup_wizard"),
    path("setup/poll/", lazy_view("whatsapp.setup_views.whatsapp_setup_poll"), name="setup_poll"),
    path("mini/<uuid:account_id>/", lazy_view("whatsapp.control_views.whatsapp_mini_site"), name="mini_site"),

    # User-side visual drag & drop bot builder (per WhatsApp account)
    path("accounts/<uuid:account_id>/visual-flows/", lazy_view("whatsapp.visual_views.visual_flow_list"), name="visual_flow_list"),
    path(
        "accounts/<uuid:account_id>/visual-flows/<uuid:flow_id>/builder/",
        lazy_view("whatsapp.visual_views.visual_flow_builder"),
        name="visual_flow_builder",
    ),
    path(
        "accounts/<uuid:account_id>/visual-flows/<uuid:flow_id>/save/",
        lazy_view("whatsapp.visual_views.visual_flow_save"),
        name="visual_flow_save",
    ),
]
