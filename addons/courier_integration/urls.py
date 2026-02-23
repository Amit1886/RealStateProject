from django.urls import path

from .views import CourierWebhookAPI, HealthAPI, ShipmentCreateAPI, ShipmentDetailAPI, ShipmentListAPI

urlpatterns = [
    path("health/", HealthAPI.as_view(), name="health"),
    path("shipments/", ShipmentListAPI.as_view(), name="shipments"),
    path("shipments/create/", ShipmentCreateAPI.as_view(), name="shipment_create"),
    path("shipments/<int:shipment_id>/", ShipmentDetailAPI.as_view(), name="shipment_detail"),
    path("webhooks/status/", CourierWebhookAPI.as_view(), name="courier_webhook"),
]
