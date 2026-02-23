from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import POSHoldBillViewSet, POSReprintLogViewSet, POSSessionViewSet, POSTerminalViewSet

router = DefaultRouter()
router.register("terminals", POSTerminalViewSet, basename="pos-terminal")
router.register("sessions", POSSessionViewSet, basename="pos-session")
router.register("hold-bills", POSHoldBillViewSet, basename="pos-hold")
router.register("reprint-logs", POSReprintLogViewSet, basename="pos-reprint")

urlpatterns = [
    path("", include(router.urls)),
]
