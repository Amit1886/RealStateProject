# full path: ~/myproject/khatapro/billing/urls.py

from django.urls import path
from . import views

app_name = "billing"

urlpatterns = [
    # Plan selection and dashboard
    path("dashboard/", views.dashboard, name="dashboard"),               # /billing/dashboard/

    # Payment related
    path("start-payment/<slug:plan_slug>/", views.start_payment, name="start_payment"),  # start payment
    path("payment/<str:invoice_number>/", views.payment_page, name="payment_page"),      # payment details
    path("payment-return/", views.payment_return, name="payment_return"),                # redirect after gateway
    path("payment-success/<int:plan_id>/", views.payment_success, name="checkout"),
    path("choose-plan/", views.choose_plan, name="choose_plan"),

    # Webhook handlers (for gateways like Razorpay, PhonePe, Paytm etc.)
    path("webhook/<str:provider>/", views.gateway_webhook, name="gateway_webhook"),
]
