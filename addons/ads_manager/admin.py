from django.contrib import admin

from .models import ABExperiment, AdAccount, Campaign, CampaignMetric


@admin.register(AdAccount)
class AdAccountAdmin(admin.ModelAdmin):
    list_display = ("platform", "account_id", "branch_code", "is_active")
    list_filter = ("platform", "is_active", "branch_code")


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("name", "account", "status", "daily_budget", "branch_code")
    list_filter = ("status", "account__platform", "branch_code")


@admin.register(CampaignMetric)
class CampaignMetricAdmin(admin.ModelAdmin):
    list_display = ("campaign", "metric_date", "spend", "revenue", "conversions")
    list_filter = ("metric_date",)


@admin.register(ABExperiment)
class ABExperimentAdmin(admin.ModelAdmin):
    list_display = ("name", "campaign", "winner", "is_active")
    list_filter = ("is_active", "branch_code")
