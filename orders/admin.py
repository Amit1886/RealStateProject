from django.contrib import admin

from .models import Order, OrderItem, OrderReturn, POSBill

admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(POSBill)
admin.site.register(OrderReturn)
