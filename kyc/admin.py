from django.contrib import admin

from .models import KYCDocument, KYCProfile


class KYCDocumentInline(admin.TabularInline):
    model = KYCDocument
    extra = 0


@admin.register(KYCProfile)
class KYCProfileAdmin(admin.ModelAdmin):
    inlines = [KYCDocumentInline]
    list_display = ("user", "full_name", "status", "verified_at", "updated_at")
    list_filter = ("status",)
    search_fields = ("user__email", "full_name", "pan_number", "aadhaar_number_masked")


@admin.register(KYCDocument)
class KYCDocumentAdmin(admin.ModelAdmin):
    list_display = ("profile", "document_type", "status", "uploaded_at", "reviewed_at")
    list_filter = ("document_type", "status")
    search_fields = ("profile__user__email", "document_number_masked")

