from django.contrib import admin
from commerce.models import Product, StockEntry


# Register your models here.
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit', 'price', 'stock')
    search_fields = ('name',)


@admin.register(StockEntry)
class StockEntryAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'entry_type', 'date')
    list_filter = ('entry_type', 'date')



