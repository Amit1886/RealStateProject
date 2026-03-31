from django.contrib import admin

from intelligence.models import (
    AggregatedProperty,
    DemandHeatmapSnapshot,
    InvestorMatch,
    InvestorProfile,
    LeadPurchase,
    PremiumLeadListing,
    PriceTrendSnapshot,
    PropertyAlertSubscription,
    PropertyImportBatch,
    RealEstateDocument,
)


@admin.register(PropertyImportBatch)
class PropertyImportBatchAdmin(admin.ModelAdmin):
    list_display = ["id", "source_name", "source_type", "status", "fetched_count", "inserted_count", "duplicate_count", "created_at"]
    list_filter = ["source_type", "status"]
    search_fields = ["source_name"]


@admin.register(AggregatedProperty)
class AggregatedPropertyAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "source", "city", "property_type", "price", "is_duplicate", "matched_property", "import_date"]
    list_filter = ["source", "property_type", "is_duplicate", "aggregated_property"]
    search_fields = ["title", "normalized_title", "source_reference", "duplicate_key", "city", "district"]


@admin.register(DemandHeatmapSnapshot)
class DemandHeatmapSnapshotAdmin(admin.ModelAdmin):
    list_display = ["id", "snapshot_date", "city", "district", "demand_score", "low_supply_score", "hot_investment_score"]
    list_filter = ["snapshot_date", "city", "district"]


@admin.register(PriceTrendSnapshot)
class PriceTrendSnapshotAdmin(admin.ModelAdmin):
    list_display = ["id", "snapshot_date", "city", "district", "property_type", "average_price", "price_change_percent", "sample_size"]
    list_filter = ["snapshot_date", "city", "district", "property_type"]


@admin.register(InvestorProfile)
class InvestorProfileAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "investment_budget", "risk_level", "active", "alerts_enabled", "created_at"]
    list_filter = ["risk_level", "active", "alerts_enabled"]
    search_fields = ["name", "email", "phone"]


@admin.register(InvestorMatch)
class InvestorMatchAdmin(admin.ModelAdmin):
    list_display = ["id", "investor", "property", "project", "score", "expected_roi_percent", "status", "created_at"]
    list_filter = ["status"]


@admin.register(PropertyAlertSubscription)
class PropertyAlertSubscriptionAdmin(admin.ModelAdmin):
    list_display = ["id", "customer", "city", "district", "property_type", "is_active", "updated_at"]
    list_filter = ["is_active", "city", "district", "property_type"]


@admin.register(PremiumLeadListing)
class PremiumLeadListingAdmin(admin.ModelAdmin):
    list_display = ["id", "lead", "category", "price", "status", "buyer_agent", "created_at"]
    list_filter = ["category", "status"]


@admin.register(LeadPurchase)
class LeadPurchaseAdmin(admin.ModelAdmin):
    list_display = ["id", "listing", "buyer_agent", "amount", "purchased_at"]


@admin.register(RealEstateDocument)
class RealEstateDocumentAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "document_type", "access_scope", "uploaded_by", "created_at"]
    list_filter = ["document_type", "access_scope"]
    search_fields = ["title", "property__title", "lead__name"]
