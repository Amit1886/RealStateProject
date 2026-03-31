from django.contrib import admin

from .models import GroupVisit, GroupVisitAttendance, SiteVisit


@admin.register(GroupVisit)
class GroupVisitAdmin(admin.ModelAdmin):
    list_display = ["id", "agent", "visit_date", "location", "created_by"]
    list_filter = ["visit_date"]
    search_fields = ["agent__name", "location"]


@admin.register(GroupVisitAttendance)
class GroupVisitAttendanceAdmin(admin.ModelAdmin):
    list_display = ["id", "group_visit", "lead", "attendance_status", "checked_in_at", "created_at"]
    list_filter = ["attendance_status", "created_at"]
    search_fields = ["lead__name", "group_visit__location"]


@admin.register(SiteVisit)
class SiteVisitAdmin(admin.ModelAdmin):
    list_display = ["id", "lead", "agent", "group_visit", "visit_date", "status", "is_no_show", "is_group_visit"]
    list_filter = ["status", "visit_date", "is_no_show", "is_group_visit"]
    autocomplete_fields = ["lead", "agent"]
    search_fields = ["lead__name", "agent__name", "location"]
