from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import OrderItemViewSet, OrderReturnViewSet, OrderViewSet, POSBillViewSet

router = DefaultRouter()
router.register("orders", OrderViewSet, basename="order")
router.register("order-items", OrderItemViewSet, basename="order-item")
router.register("pos-bills", POSBillViewSet, basename="pos-bill")
router.register("order-returns", OrderReturnViewSet, basename="order-return")

urlpatterns = [path("", include(router.urls))]
