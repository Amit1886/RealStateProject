from django.contrib import admin

from .models import PropertyVerification, VerificationDocument


@admin.register(PropertyVerification)
class PropertyVerificationAdmin(admin.ModelAdmin):
    list_display = ("id", "property", "requested_by", "status", "reviewed_by", "created_at")
    list_filter = ("status", "company")
    search_fields = ("property__title", "requested_by__email")


@admin.register(VerificationDocument)
class VerificationDocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "verification", "document_type", "uploaded_by", "created_at")
    list_filter = ("document_type",)
    search_fields = ("title", "verification__property__title")

