from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DealViewSet, PaymentViewSet

router = DefaultRouter()
router.register("deals", DealViewSet, basename="deals")
router.register("payments", PaymentViewSet, basename="deal-payments")

urlpatterns = [
    path("create/", DealViewSet.as_view({"post": "create"}), name="deals-create"),
    path("", include(router.urls)),
]
