from django.contrib import admin

from .models import Category, Product, ProductPriceRule, WarehouseInventory

admin.site.register(Category)
admin.site.register(Product)
admin.site.register(ProductPriceRule)
admin.site.register(WarehouseInventory)
