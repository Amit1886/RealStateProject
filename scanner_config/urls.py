from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ScanEventViewSet, ScannerConfigViewSet

router = DefaultRouter()
router.register("configs", ScannerConfigViewSet, basename="scanner-config")
router.register("events", ScanEventViewSet, basename="scan-event")

urlpatterns = [path("", include(router.urls))]
