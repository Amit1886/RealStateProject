from django.urls import path

from .views import (
    StorefrontOrderCreateAPI,
    StorefrontOrderListAPI,
    StorefrontPaymentSuccessAPI,
    StorefrontProductListAPI,
    SyncProductsAPI,
)
from .storefront_views import PublicCheckoutAPI, PublicOrderStatusAPI, PublicPaymentCapturedWebhookAPI, PublicProductListAPI

urlpatterns = [
    path("products/", StorefrontProductListAPI.as_view(), name="storefront_products"),
    path("products/sync/", SyncProductsAPI.as_view(), name="storefront_sync_products"),
    path("orders/", StorefrontOrderListAPI.as_view(), name="storefront_orders"),
    path("orders/create/", StorefrontOrderCreateAPI.as_view(), name="storefront_order_create"),
    path("orders/<int:order_id>/payment-success/", StorefrontPaymentSuccessAPI.as_view(), name="storefront_payment_success"),
    # Public storefront APIs (separate frontend can consume these).
    path("storefront/products/", PublicProductListAPI.as_view(), name="public_products"),
    path("storefront/checkout/", PublicCheckoutAPI.as_view(), name="public_checkout"),
    path("storefront/orders/<str:order_number>/status/", PublicOrderStatusAPI.as_view(), name="public_order_status"),
    path("webhooks/payment-captured/", PublicPaymentCapturedWebhookAPI.as_view(), name="payment_captured_webhook"),
]
