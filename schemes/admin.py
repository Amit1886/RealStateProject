from django.contrib import admin

from .models import Scheme, UserSchemeMatch


@admin.register(Scheme)
class SchemeAdmin(admin.ModelAdmin):
    list_display = ("title", "state", "city", "income_limit", "ownership_status", "active")
    list_filter = ("active", "ownership_status", "state")
    search_fields = ("title", "city", "district", "state")


@admin.register(UserSchemeMatch)
class UserSchemeMatchAdmin(admin.ModelAdmin):
    list_display = ("user", "scheme", "match_score", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("user__email", "scheme__title")

