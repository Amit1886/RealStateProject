from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PayoutViewSet

router = DefaultRouter()
router.register("payouts", PayoutViewSet, basename="payouts")

urlpatterns = [path("", include(router.urls))]
