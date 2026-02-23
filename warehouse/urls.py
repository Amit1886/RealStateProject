from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import WarehouseStaffAssignmentViewSet, WarehouseViewSet

router = DefaultRouter()
router.register("warehouses", WarehouseViewSet, basename="warehouse")
router.register("staff-assignments", WarehouseStaffAssignmentViewSet, basename="warehouse-staff")

urlpatterns = [path("", include(router.urls))]
