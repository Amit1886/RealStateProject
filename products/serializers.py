from rest_framework import serializers

from .models import Category, Product, ProductPriceRule, WarehouseInventory


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"


class ProductPriceRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductPriceRule
        fields = "__all__"


class WarehouseInventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = WarehouseInventory
        fields = "__all__"
