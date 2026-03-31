from django.contrib import admin
from .models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "domain", "currency", "active", "created_at")
    search_fields = ("name", "domain")
    list_filter = ("active",)
