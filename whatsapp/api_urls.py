from django.urls import include, path
from rest_framework.routers import DefaultRouter

from realstateproject.lazy_views import lazy_viewset

router = DefaultRouter()
router.register("accounts", lazy_viewset("whatsapp.api_views.WhatsAppAccountViewSet"), basename="wa-account")
router.register("bots", lazy_viewset("whatsapp.api_views.BotViewSet"), basename="wa-bot")
router.register("bot-flows", lazy_viewset("whatsapp.api_views.BotFlowViewSet"), basename="wa-bot-flow")
router.register("bot-messages", lazy_viewset("whatsapp.api_views.BotMessageViewSet"), basename="wa-bot-message")
router.register("customers", lazy_viewset("whatsapp.api_views.CustomerViewSet"), basename="wa-customer")
router.register("bot-templates", lazy_viewset("whatsapp.api_views.BotTemplateViewSet"), basename="wa-bot-template")
router.register("broadcasts", lazy_viewset("whatsapp.api_views.BroadcastCampaignViewSet"), basename="wa-broadcast")
router.register("message-logs", lazy_viewset("whatsapp.api_views.MessageLogViewSet"), basename="wa-message-log")

urlpatterns = [path("", include(router.urls))]
