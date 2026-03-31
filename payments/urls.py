from django.urls import path
from realstateproject.lazy_views import lazy_view

app_name = "payments"

urlpatterns = [
    path("checkout/", lazy_view("payments.views.checkout"), name="checkout"),
    path("history/", lazy_view("payments.views.payment_history"), name="history"),
    path("orders/<uuid:reference_id>/", lazy_view("payments.views.order_detail"), name="order_detail"),
    path("orders/<uuid:reference_id>/simulate/", lazy_view("payments.views.simulate_success_view"), name="simulate_success"),
    path("success/<uuid:reference_id>/", lazy_view("payments.views.payment_success"), name="success"),
    path("webhooks/<str:gateway>/", lazy_view("payments.views.webhook"), name="webhook"),
]
