from django.contrib import admin

from .models import PaymentGatewayConfig, StorefrontOrder, StorefrontOrderItem, StorefrontPayment, StorefrontProduct, StorefrontSyncLog


class StorefrontOrderItemInline(admin.TabularInline):
    model = StorefrontOrderItem
    extra = 0


@admin.register(StorefrontProduct)
class StorefrontProductAdmin(admin.ModelAdmin):
    list_display = ("sku", "product_name", "price", "available_stock", "selected_for_online", "is_published")
    list_filter = ("selected_for_online", "is_published", "branch_code")
    search_fields = ("sku", "product_name")


@admin.register(StorefrontOrder)
class StorefrontOrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "customer_name", "status", "payment_status", "synced_to_billing")
    list_filter = ("status", "payment_status", "synced_to_billing", "branch_code")
    search_fields = ("order_number", "customer_name", "customer_phone")
    inlines = [StorefrontOrderItemInline]


@admin.register(StorefrontSyncLog)
class StorefrontSyncLogAdmin(admin.ModelAdmin):
    list_display = ("direction", "ref", "status", "created_at")
    list_filter = ("direction", "status")


@admin.register(StorefrontPayment)
class StorefrontPaymentAdmin(admin.ModelAdmin):
    list_display = ("gateway", "payment_ref", "status", "amount", "currency", "created_at")
    list_filter = ("gateway", "status", "branch_code")
    search_fields = ("payment_ref", "order__order_number")


@admin.register(PaymentGatewayConfig)
class PaymentGatewayConfigAdmin(admin.ModelAdmin):
    list_display = ("branch_code", "provider", "is_active", "sandbox", "updated_at")
    list_filter = ("provider", "is_active", "sandbox", "branch_code")
    search_fields = ("provider", "branch_code", "key_id")
