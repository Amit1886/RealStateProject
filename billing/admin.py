from django.contrib import admin
from .models import (
    Plan, BillingInvoice, Subscription, PaymentGateway,
    Commerce, Payment, Order, OrderItem,
    Warehouse, Stock, ChatThread, ChatMessage,
    Notification, PartyPortal
)


# =========================
# 💳 PLAN ADMIN
# =========================
@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'active', 'created_at')
    list_filter = ('active',)
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


# =========================
# 🧾 INVOICE ADMIN
# =========================
@admin.register(BillingInvoice)
class BillingInvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "user", "plan", "amount", "status", "created_at")
    search_fields = ("invoice_number", "user__username")

# =========================
# 📦 SUBSCRIPTION ADMIN
# =========================
@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'status', 'start_date', 'end_date', 'created_at')
    list_filter = ('status', 'plan')
    search_fields = ('user__username', 'plan__name')


# =========================
# 🏦 PAYMENT GATEWAY ADMIN
# =========================
@admin.register(PaymentGateway)
class PaymentGatewayAdmin(admin.ModelAdmin):
    list_display = ('name', 'provider', 'active', 'created_at')
    list_filter = ('provider', 'active')
    search_fields = ('name',)


# =========================
# 🏪 COMMERCE ADMIN
# =========================
@admin.register(Commerce)
class CommerceAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'user', 'category', 'contact_number', 'created_at')
    search_fields = ('business_name', 'user__username', 'contact_number')
    list_filter = ('category',)


# =========================
# 💰 PAYMENT ADMIN
# =========================
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'amount', 'payment_method', 'payment_status', 'created_at')
    list_filter = ('payment_status', 'payment_method')
    search_fields = ('transaction_id', 'order__id')


# =========================
# 🧾 ORDER ADMIN
# =========================
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'payment_status', 'total_amount', 'order_date')
    list_filter = ('status', 'payment_status')
    search_fields = ('user__username',)
    ordering = ('-order_date',)


# =========================
# 📦 ORDER ITEM ADMIN
# =========================
@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product_name', 'quantity', 'price')
    search_fields = ('product_name',)
    list_filter = ('order',)


# =========================
# 🏢 WAREHOUSE ADMIN
# =========================
@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'capacity')
    search_fields = ('name', 'location')


# =========================
# 📊 STOCK ADMIN
# =========================
@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'warehouse', 'quantity', 'updated_at')
    list_filter = ('warehouse',)
    search_fields = ('product_name',)


# =========================
# 💬 CHAT THREAD ADMIN
# =========================
@admin.register(ChatThread)
class ChatThreadAdmin(admin.ModelAdmin):
    list_display = ('user1', 'user2', 'created_at')
    search_fields = ('user1__username', 'user2__username')


# =========================
# 💭 CHAT MESSAGE ADMIN
# =========================
@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('thread', 'sender', 'message', 'timestamp', 'is_read')
    list_filter = ('is_read',)
    search_fields = ('sender__username', 'message')


# =========================
# 🔔 NOTIFICATION ADMIN
# =========================
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'is_read', 'created_at')
    list_filter = ('is_read',)
    search_fields = ('title', 'user__username')


# =========================
# 🌐 PARTY PORTAL ADMIN
# =========================
@admin.register(PartyPortal)
class PartyPortalAdmin(admin.ModelAdmin):
    list_display = ('name', 'link', 'created_at')
    search_fields = ('name', 'link')
