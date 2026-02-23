from rest_framework import filters, permissions, viewsets

from .models import Category, Product, ProductPriceRule, WarehouseInventory
from .serializers import CategorySerializer, ProductPriceRuleSerializer, ProductSerializer, WarehouseInventorySerializer


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related("category").all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "sku", "barcode"]
    ordering_fields = ["name", "created_at", "mrp"]


class ProductPriceRuleViewSet(viewsets.ModelViewSet):
    queryset = ProductPriceRule.objects.select_related("product").all()
    serializer_class = ProductPriceRuleSerializer
    permission_classes = [permissions.IsAuthenticated]


class WarehouseInventoryViewSet(viewsets.ModelViewSet):
    queryset = WarehouseInventory.objects.select_related("warehouse", "product").all()
    serializer_class = WarehouseInventorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["warehouse__name", "product__name", "product__sku"]
    ordering_fields = ["updated_at", "available_qty", "reserved_qty"]
