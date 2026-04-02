# full path: ~/myproject/khatapro/billing/urls.py

from django.urls import path
from realstateproject.lazy_views import lazy_view

app_name = "billing"

urlpatterns = [
    # Plan selection and dashboard
    path("dashboard/", lazy_view("billing.views.dashboard"), name="dashboard"),                  # /billing/dashboard/
    path("commerce-dashboard/", lazy_view("billing.views.commerce_dashboard"), name="commerce_dashboard"),

    # Payment related
    path("payment-success/<int:plan_id>/", lazy_view("billing.views.payment_success"), name="payment-success"),
    path("checkout/", lazy_view("billing.views.checkout"), name="checkout"),
    path("webhook/<str:provider>/", lazy_view("billing.views.gateway_webhook"), name="webhook"),
    path("choose-plan/", lazy_view("billing.views.choose_plan"), name="choose_plan"),
    path("upgrade/", lazy_view("billing.views.upgrade_plan"), name="upgrade_plan"),
    path("plan-management/", lazy_view("billing.views.plan_management"), name="plan_management"),
    path("upgrade/start/<int:plan_id>/", lazy_view("billing.views.start_upgrade"), name="start_upgrade"),
    path("history/", lazy_view("billing.views.billing_history"), name="billing_history"),
    path("invoices/", lazy_view("billing.views.invoice_list"), name="invoice_list"),
    path("invoices/<str:invoice_number>/", lazy_view("billing.views.invoice_detail"), name="invoice_detail"),
    path("invoices/<str:invoice_number>/pdf/", lazy_view("billing.views.invoice_pdf"), name="invoice_pdf"),
    path("reports/gst/", lazy_view("billing.views.gst_report"), name="gst_report"),

    # Admin feature matrix
    path("admin/feature-matrix/", lazy_view("billing.views.feature_matrix"), name="feature_matrix"),
    path("admin/feature-matrix/save/", lazy_view("billing.views.feature_matrix_save"), name="feature_matrix_save"),



    # Webhook handlers (for gateways like Razorpay, PhonePe, Paytm etc.)
    #path("webhook/<str:provider>/", views.gateway_webhook, name="gateway_webhook"),
]
