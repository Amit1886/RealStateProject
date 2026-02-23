from django.contrib import admin

from addons.courier_integration.models import CourierProviderConfig, Shipment, ShipmentEvent


@admin.register(CourierProviderConfig)
class CourierProviderConfigAdmin(admin.ModelAdmin):
    list_display = ("branch_code", "provider", "is_active", "sandbox", "updated_at")
    list_filter = ("provider", "is_active", "sandbox", "branch_code")
    search_fields = ("provider", "branch_code")


class ShipmentEventInline(admin.TabularInline):
    model = ShipmentEvent
    extra = 0
    readonly_fields = ("event_type", "payload", "created_at")


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ("provider", "status", "ref_type", "ref", "awb", "created_at")
    list_filter = ("provider", "status", "ref_type", "branch_code")
    search_fields = ("ref", "awb", "tracking_number")
    inlines = [ShipmentEventInline]

