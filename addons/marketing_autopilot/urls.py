from django.urls import path

from .views import CreativeAssetCreateAPI, MarketingScheduleCreateAPI, MarketingScheduleListAPI, MarketingTextGenAPI

urlpatterns = [
    path("text/generate/", MarketingTextGenAPI.as_view(), name="marketing_text_generate"),
    path("schedules/", MarketingScheduleListAPI.as_view(), name="marketing_schedules"),
    path("schedules/create/", MarketingScheduleCreateAPI.as_view(), name="marketing_schedule_create"),
    path("creative-assets/create/", CreativeAssetCreateAPI.as_view(), name="marketing_creative_create"),
]
