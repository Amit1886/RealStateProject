from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DeliveryAssignmentViewSet, DeliveryTrackingPingViewSet

router = DefaultRouter()
router.register("assignments", DeliveryAssignmentViewSet, basename="delivery-assignment")
router.register("tracking", DeliveryTrackingPingViewSet, basename="delivery-tracking")

urlpatterns = [path("", include(router.urls))]
