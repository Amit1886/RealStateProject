# full path: ~/myproject/khatapro/billing/urls.py

from django.urls import path
from . import views

app_name = "billing"

urlpatterns = [
    # Plan selection and dashboard
    path("dashboard/", views.dashboard, name="dashboard"),                  # /billing/dashboard/
    path("dashboard/", views.commerce_dashboard, name="commerce_dashboard"),

    # Payment related
    path("payment-success/<int:plan_id>/", views.payment_success, name="payment-success"),
    path("checkout/", views.checkout, name="checkout"),
    path("choose-plan/", views.choose_plan, name="choose_plan"),
    path("upgrade/", views.upgrade_plan, name="upgrade_plan"),



    # Webhook handlers (for gateways like Razorpay, PhonePe, Paytm etc.)
    #path("webhook/<str:provider>/", views.gateway_webhook, name="gateway_webhook"),
]
