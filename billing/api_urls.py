from django.urls import include, path
from rest_framework.routers import DefaultRouter
from realstateproject.lazy_views import lazy_view, lazy_viewset

router = DefaultRouter()
router.register("invoices", lazy_viewset("billing.api_views.InvoiceViewSet"), basename="billing-invoices")
router.register("invoice-items", lazy_viewset("billing.api_views.InvoiceItemViewSet"), basename="billing-invoice-items")
router.register("gst", lazy_viewset("billing.api_views.GSTDetailViewSet"), basename="billing-gst")

urlpatterns = [
    path("invoice/create/", lazy_view("billing.api_views.InvoiceCreateAPIView"), name="invoice-create"),
    path("", include(router.urls)),
]
