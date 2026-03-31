import csv

from django.contrib import admin
from django.http import HttpResponse

from .models import (
    Builder,
    Lead,
    LeadActivity,
    LeadAssignment,
    LeadAssignmentLog,
    LeadImportBatch,
    LeadSource,
    Property,
    PropertyFeature,
    PropertyImage,
    PropertyLocation,
    PropertyMedia,
    PropertyProject,
    ProjectPhase,
    PropertyVideo,
    PropertyWishlist,
)


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    date_hierarchy = "created_at"
    list_select_related = ("assigned_agent", "assigned_to", "company", "source_config", "converted_customer")
    list_display = (
        "id",
        "name",
        "mobile",
        "source",
        "status",
        "deal_value",
        "assigned_agent",
        "assigned_to",
        "company",
        "is_duplicate",
        "converted_customer",
        "customer_type",
        "reliability_score",
        "no_show_count",
        "is_locked",
        "locked_by",
        "locked_at",
        "stage_updated_at",
        "stage_deadline",
        "is_overdue",
        "distribution_level",
        "created_at",
    )
    list_filter = ("source", "status", "stage", "interest_type", "customer_type", "company", "assigned_agent", "distribution_level", "is_duplicate", "is_overdue", "is_locked")
    search_fields = ("name", "mobile", "email", "city", "district", "state", "pincode_text")
    actions = (
        "mark_selected_contacted",
        "mark_selected_follow_up",
        "mark_selected_converted",
        "mark_selected_closed",
        "lock_selected",
        "unlock_selected",
        "export_selected_csv",
    )

    @admin.action(description="Mark selected as Contacted")
    def mark_selected_contacted(self, request, queryset):
        for lead in queryset:
            lead.mark_status(Lead.Status.CONTACTED, actor=request.user, note="Bulk admin action")

    @admin.action(description="Mark selected as Follow Up")
    def mark_selected_follow_up(self, request, queryset):
        for lead in queryset:
            lead.mark_status(Lead.Status.FOLLOW_UP, actor=request.user, note="Bulk admin action")

    @admin.action(description="Mark selected as Converted")
    def mark_selected_converted(self, request, queryset):
        for lead in queryset:
            lead.mark_status(Lead.Status.CONVERTED, actor=request.user, note="Bulk admin action")

    @admin.action(description="Mark selected as Closed")
    def mark_selected_closed(self, request, queryset):
        for lead in queryset:
            lead.mark_status(Lead.Status.CLOSED, actor=request.user, note="Bulk admin action")

    @admin.action(description="Lock selected leads")
    def lock_selected(self, request, queryset):
        from .services import lock_lead

        for lead in queryset.select_related("assigned_agent"):
            lock_lead(lead, actor=request.user, reason="Bulk admin lock")

    @admin.action(description="Unlock selected leads")
    def unlock_selected(self, request, queryset):
        from .services import unlock_lead

        for lead in queryset:
            unlock_lead(lead, actor=request.user, reason="Bulk admin unlock")

    @admin.action(description="Export selected leads as CSV")
    def export_selected_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="selected-leads.csv"'
        writer = csv.writer(response)
        writer.writerow(["ID", "Name", "Mobile", "Email", "Source", "Status", "Stage", "Assigned Agent", "Created At"])
        for lead in queryset.select_related("assigned_agent"):
            writer.writerow(
                [
                    lead.id,
                    lead.name,
                    lead.mobile,
                    lead.email,
                    lead.get_source_display(),
                    lead.get_status_display(),
                    lead.get_stage_display(),
                    getattr(lead.assigned_agent, "name", ""),
                    lead.created_at,
                ]
            )
        return response


@admin.register(LeadActivity)
class LeadActivityAdmin(admin.ModelAdmin):
    list_display = ("id", "lead", "activity_type", "actor", "created_at")
    list_filter = ("activity_type",)


@admin.register(LeadAssignmentLog)
class LeadAssignmentLogAdmin(admin.ModelAdmin):
    list_display = ("id", "lead", "agent", "assignment_type", "matched_on", "assigned_by", "created_at")
    list_filter = ("assignment_type", "matched_on")
    search_fields = ("lead__name", "lead__mobile", "agent__name")


@admin.register(LeadAssignment)
class LeadAssignmentAdmin(admin.ModelAdmin):
    list_display = ("id", "lead", "agent", "assignment_type", "matched_on", "is_active", "response_due_at", "created_at")
    list_filter = ("assignment_type", "matched_on", "is_active")
    search_fields = ("lead__name", "lead__mobile", "agent__name")


@admin.register(LeadSource)
class LeadSourceAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "kind", "source_value", "is_active", "auto_assign", "company", "updated_at")
    list_filter = ("kind", "source_value", "is_active")
    search_fields = ("name", "slug", "endpoint_url")
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ("is_active", "auto_assign")


@admin.register(LeadImportBatch)
class LeadImportBatchAdmin(admin.ModelAdmin):
    list_display = ("id", "import_type", "source_name", "status", "total_rows", "created_leads", "duplicate_rows", "failed_rows", "created_at")
    list_filter = ("import_type", "status")
    search_fields = ("source_name", "external_reference")
    readonly_fields = ("created_at", "updated_at", "error_report", "payload")


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "listing_type", "property_type", "city", "district", "state", "price", "status", "aggregated_property", "data_source", "assigned_agent")
    list_filter = ("listing_type", "property_type", "status", "aggregated_property", "data_source", "city", "district", "state")
    search_fields = ("title", "city", "district", "state", "pin_code", "source_reference")


@admin.register(PropertyMedia)
class PropertyMediaAdmin(admin.ModelAdmin):
    list_display = ("id", "property", "media_type", "sort_order", "created_at")
    list_filter = ("media_type",)


@admin.register(PropertyWishlist)
class PropertyWishlistAdmin(admin.ModelAdmin):
    list_display = ("id", "property", "user", "created_at")
    search_fields = ("property__title", "user__email", "user__mobile")


@admin.register(PropertyLocation)
class PropertyLocationAdmin(admin.ModelAdmin):
    list_display = ("id", "property", "city", "district", "state", "pin_code", "updated_at")
    list_filter = ("city", "district", "state")
    search_fields = ("property__title", "city", "district", "state", "pin_code")


@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    list_display = ("id", "property", "is_primary", "sort_order", "created_at")
    list_filter = ("is_primary",)


@admin.register(PropertyVideo)
class PropertyVideoAdmin(admin.ModelAdmin):
    list_display = ("id", "property", "caption", "created_at")


@admin.register(PropertyFeature)
class PropertyFeatureAdmin(admin.ModelAdmin):
    list_display = ("id", "property", "feature_name", "feature_value", "created_at")
    search_fields = ("property__title", "feature_name", "feature_value")


@admin.register(Builder)
class BuilderAdmin(admin.ModelAdmin):
    list_display = ("id", "company_name", "registration_number", "city", "contact", "contact_email", "verified")
    list_filter = ("verified", "city")
    search_fields = ("company_name", "name", "registration_number", "contact", "contact_email")


@admin.register(PropertyProject)
class PropertyProjectAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "builder", "city", "starting_price", "max_price", "launch_date", "status", "construction_status", "pre_launch", "approved", "completion_date")
    list_filter = ("approved", "pre_launch", "status", "construction_status", "city")
    search_fields = ("title", "builder__company_name", "builder__name", "city")


@admin.register(ProjectPhase)
class ProjectPhaseAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "name", "status", "start_date", "end_date", "created_at")
    list_filter = ("status", "start_date")
    search_fields = ("project__title", "name")
