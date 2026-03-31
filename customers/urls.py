from django.urls import include, path
from rest_framework.routers import DefaultRouter

from customers.views import CustomerPreferenceViewSet, CustomerViewSet

router = DefaultRouter()
router.register("customers", CustomerViewSet, basename="customers")
router.register("preferences", CustomerPreferenceViewSet, basename="customer-preferences")

urlpatterns = [path("", include(router.urls))]
