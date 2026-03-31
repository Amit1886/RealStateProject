from django.urls import include, path
from rest_framework.routers import DefaultRouter

from communication.views import CommunicationEventAPIView, EmailLogViewSet, MessageLogViewSet, SMSLogViewSet

router = DefaultRouter()
router.register("messages", MessageLogViewSet, basename="communication-messages")
router.register("emails", EmailLogViewSet, basename="communication-emails")
router.register("sms", SMSLogViewSet, basename="communication-sms")

urlpatterns = [
    path("events/", CommunicationEventAPIView.as_view(), name="communication-events"),
    path("", include(router.urls)),
]
