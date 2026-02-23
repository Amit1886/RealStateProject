from django.urls import path

from .views import CampaignBudgetGuardAPI, CampaignListAPI, CampaignROIApi, CampaignSyncAPI

urlpatterns = [
    path("campaigns/", CampaignListAPI.as_view(), name="ads_campaign_list"),
    path("campaigns/<int:campaign_id>/roi/", CampaignROIApi.as_view(), name="ads_campaign_roi"),
    path("campaigns/<int:campaign_id>/sync/", CampaignSyncAPI.as_view(), name="ads_campaign_sync"),
    path("campaigns/<int:campaign_id>/budget-guard/", CampaignBudgetGuardAPI.as_view(), name="ads_campaign_budget_guard"),
]
