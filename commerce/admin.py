from django.contrib import admin
from .models import (
    Warehouse, Category, Product, Stock,
    ChatThread, ChatMessage,
    Order, OrderItem, Invoice, Payment, Notification,
    Coupon, UserCoupon, CouponUsage
)

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("name", "location", "capacity", "created_at")

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "stock", "sku", "gst_rate", "owner")
    search_fields = ("name", "sku")

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "party", "status", "created_at", "owner")
    list_filter = ("status", "created_at")

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "product", "qty", "price")

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "order", "amount", "status", "created_at")

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("invoice", "amount", "method", "reference", "created_at")

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ("product", "warehouse", "quantity", "updated_at")

@admin.register(ChatThread)
class ChatThreadAdmin(admin.ModelAdmin):
    list_display = ("party", "created_at")

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("thread", "sent_by", "text", "created_at")

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("message", "is_read", "created_at")

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("title", "code", "coupon_type", "discount_value", "usage_limit", "is_active", "valid_until")
    list_filter = ("coupon_type", "is_active", "valid_from", "valid_until")
    search_fields = ("title", "code")
    readonly_fields = ("created_at", "updated_at")

@admin.register(UserCoupon)
class UserCouponAdmin(admin.ModelAdmin):
    list_display = ("user", "coupon", "is_used", "assigned_at")
    list_filter = ("is_used", "assigned_at")
    search_fields = ("user__username", "coupon__code")

@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
    list_display = ("coupon", "user", "order", "discount_amount", "used_at")
    list_filter = ("used_at",)
    search_fields = ("coupon__code", "user__username")
