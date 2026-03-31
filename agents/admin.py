from django.contrib import admin

from .models import Agent, AgentActivityLog, AgentCoverageArea, AgentLocationLog, AgentPerformanceSnapshot, AgentRiskProfile, AgentSession, AgentTransfer, AgentVerification
from .wallet import AgentWallet, WalletTransaction


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "phone", "license_number", "city", "district", "state", "approval_status", "specialization", "company", "is_active", "kyc_status", "last_assigned_at"]
    list_filter = ["company", "approval_status", "is_active", "kyc_status", "specialization", "city", "district", "state"]
    search_fields = ["name", "phone", "user__email", "user__mobile", "pincodes", "pin_code", "city", "district", "state"]
    autocomplete_fields = ["user", "company", "service_areas", "parent_agent"]
    readonly_fields = ["created_at", "updated_at", "total_sales", "total_visits", "last_assigned_at", "kyc_verified_at"]


@admin.register(AgentWallet)
class AgentWalletAdmin(admin.ModelAdmin):
    list_display = ["id", "agent", "balance", "total_earned", "total_withdrawn", "updated_at"]
    search_fields = ["agent__name", "agent__user__email"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ["id", "agent", "amount", "type", "source", "status", "created_at"]
    list_filter = ["type", "status", "source"]
    search_fields = ["agent__name", "note"]
    readonly_fields = ["created_at"]


@admin.register(AgentLocationLog)
class AgentLocationLogAdmin(admin.ModelAdmin):
    list_display = ["id", "agent", "latitude", "longitude", "accuracy", "timestamp"]
    list_filter = ["timestamp"]
    search_fields = ["agent__name"]


@admin.register(AgentRiskProfile)
class AgentRiskProfileAdmin(admin.ModelAdmin):
    list_display = ["id", "agent", "risk_score", "risk_level", "last_evaluated"]
    list_filter = ["risk_level"]
    search_fields = ["agent__name"]


@admin.register(AgentActivityLog)
class AgentActivityLogAdmin(admin.ModelAdmin):
    list_display = ["id", "agent", "action", "created_at"]
    list_filter = ["action"]
    search_fields = ["agent__name"]


@admin.register(AgentSession)
class AgentSessionAdmin(admin.ModelAdmin):
    list_display = ["id", "agent", "login_at", "logout_at", "ip_address"]
    search_fields = ["agent__name", "ip_address"]


@admin.register(AgentPerformanceSnapshot)
class AgentPerformanceSnapshotAdmin(admin.ModelAdmin):
    list_display = ["id", "agent", "date", "total_leads", "closed_leads", "closing_ratio", "leads_assigned", "leads_closed", "revenue", "risk_score"]
    list_filter = ["date"]


@admin.register(AgentCoverageArea)
class AgentCoverageAreaAdmin(admin.ModelAdmin):
    list_display = ["id", "agent", "pin_code", "city", "district", "state", "is_primary", "is_active"]
    list_filter = ["is_primary", "is_active", "state", "district"]
    search_fields = ["agent__name", "pin_code", "city", "district", "state", "tehsil", "village"]


@admin.register(AgentVerification)
class AgentVerificationAdmin(admin.ModelAdmin):
    list_display = ["id", "agent", "document_type", "status", "verified_by", "reviewed_at", "created_at"]
    list_filter = ["document_type", "status", "created_at"]
    search_fields = ["agent__name", "agent__user__email", "remarks"]


@admin.register(AgentTransfer)
class AgentTransferAdmin(admin.ModelAdmin):
    list_display = ["id", "old_agent", "new_agent", "transfer_type", "reassigned_leads", "reassigned_deals", "transferred_by", "created_at"]
    list_filter = ["transfer_type", "created_at"]
    search_fields = ["old_agent__name", "new_agent__name", "reason"]
