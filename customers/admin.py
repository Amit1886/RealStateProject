from django.contrib import admin

from customers.models import Customer, CustomerPreference


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "buyer_type", "preferred_location", "preferred_budget", "city", "state", "company"]
    list_filter = ["buyer_type", "city", "district", "state", "company"]
    search_fields = ["user__email", "user__mobile", "preferred_location", "city", "district", "state", "pin_code"]


@admin.register(CustomerPreference)
class CustomerPreferenceAdmin(admin.ModelAdmin):
    list_display = ["id", "customer", "property_type", "bedrooms", "budget_min", "budget_max", "city", "is_active"]
    list_filter = ["property_type", "is_active", "city", "state"]
    search_fields = ["customer__user__email", "city", "district", "state"]
