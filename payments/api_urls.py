from django.urls import include, path
from rest_framework.routers import DefaultRouter
from realstateproject.lazy_views import lazy_view, lazy_viewset

router = DefaultRouter()
router.register("orders", lazy_viewset("payments.views.PaymentOrderViewSet"), basename="payment-orders")
router.register("transactions", lazy_viewset("payments.views.PaymentTransactionViewSet"), basename="payment-transactions")
router.register("daily-cash", lazy_viewset("payments.views.DailyCashSummaryViewSet"), basename="payment-daily-cash")

urlpatterns = [
    path("link/", lazy_view("payments.views.PaymentLinkAPIView"), name="payment-link"),
    path("webhook/", lazy_view("payments.views.webhook_any"), name="payment-webhook-generic"),
    path("webhooks/<str:gateway>/", lazy_view("payments.views.webhook"), name="payment-webhook"),
    path("", include(router.urls)),
]
