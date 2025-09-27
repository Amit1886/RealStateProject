# commerce/admin.py
from django.contrib import admin
from .models import Warehouse, Product, Stock, ChatThread, ChatMessage, PartyPortal, Order, OrderItem, Invoice, Payment, Notification

admin.site.register([Warehouse, Product, Stock, ChatThread, ChatMessage, PartyPortal, Order, OrderItem, Invoice, Payment, Notification])

