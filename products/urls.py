from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, ProductPriceRuleViewSet, ProductViewSet, WarehouseInventoryViewSet

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("products", ProductViewSet, basename="product")
router.register("price-rules", ProductPriceRuleViewSet, basename="price-rule")
router.register("inventory", WarehouseInventoryViewSet, basename="inventory")

urlpatterns = [path("", include(router.urls))]
