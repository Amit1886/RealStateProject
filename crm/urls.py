from django.urls import include, path
from rest_framework.routers import DefaultRouter

from realstateproject.lazy_views import lazy_view, lazy_viewset

router = DefaultRouter()
router.register("customers", lazy_viewset("crm.views.CustomerProfileViewSet"), basename="crm-customers")
router.register("notes", lazy_viewset("crm.views.CustomerNoteViewSet"), basename="crm-notes")
router.register("calls", lazy_viewset("crm.views.CallLogViewSet"), basename="crm-calls")
router.register("followups", lazy_viewset("crm.views.FollowUpViewSet"), basename="crm-followups")

urlpatterns = [
    path("", include(router.urls)),
    path("heatmap/", lazy_view("crm.views.HeatmapAPIView"), name="crm-heatmap"),
    path("marketplace/", lazy_view("crm.views.MarketplaceAPIView"), name="crm-marketplace"),
    path("live-map/", lazy_view("crm.views.LiveMapAPIView"), name="crm-live-map"),
    path("leaderboard/", lazy_view("crm.views.LeaderboardAPIView"), name="crm-leaderboard"),
    path("agent/stats/", lazy_view("crm.views.AgentStatsAPIView"), name="crm-agent-stats"),
]
