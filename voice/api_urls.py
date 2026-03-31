from django.urls import include, path
from rest_framework.routers import DefaultRouter

from realstateproject.lazy_views import lazy_view, lazy_viewset

router = DefaultRouter()
router.register("calls", lazy_viewset("voice.views.VoiceCallViewSet"), basename="voice-calls")
router.register("turns", lazy_viewset("voice.views.VoiceCallTurnViewSet"), basename="voice-call-turns")

urlpatterns = [
    path("qualify-lead/", lazy_view("voice.views.VoiceLeadCallAPIView"), name="voice-qualify-lead"),
    path("", include(router.urls)),
]
