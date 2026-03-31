from django.contrib import admin
from reports.models import Checklist, ChecklistItem, QueryTicket

# Commerce removed in real-estate build; skip StockEntry admin if module missing
try:
    from commerce.models import StockEntry  # type: ignore

    @admin.register(StockEntry)
    class StockEntryAdmin(admin.ModelAdmin):
        list_display = ('product', 'quantity', 'entry_type', 'date')
        list_filter = ('entry_type', 'date')
except ImportError:
    StockEntry = None


class ChecklistItemInline(admin.TabularInline):
    model = ChecklistItem
    extra = 0
    fields = ("sort_order", "text", "is_done")
    ordering = ("sort_order", "id")


@admin.register(Checklist)
class ChecklistAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "owner", "title", "status", "due_date")
    list_filter = ("status", "due_date", "created_at")
    search_fields = ("title", "notes", "owner__username", "owner__email")
    raw_id_fields = ("owner",)
    date_hierarchy = "created_at"
    inlines = [ChecklistItemInline]
    ordering = ("-created_at", "-id")


@admin.register(QueryTicket)
class QueryTicketAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "owner", "subject", "status", "priority")
    list_filter = ("status", "priority", "created_at")
    search_fields = ("subject", "description", "owner__username", "owner__email")
    raw_id_fields = ("owner",)
    date_hierarchy = "created_at"
    ordering = ("-created_at", "-id")


