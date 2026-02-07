from django.contrib import admin
from commerce.models import StockEntry


# Register your models here.

@admin.register(StockEntry)
class StockEntryAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'entry_type', 'date')
    list_filter = ('entry_type', 'date')



