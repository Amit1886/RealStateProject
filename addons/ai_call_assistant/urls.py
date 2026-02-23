from django.urls import path

from .views import CallSessionListAPI, CallStartAPI, FollowUpAPI, IVRInputAPI

urlpatterns = [
    path("calls/", CallSessionListAPI.as_view(), name="call_list"),
    path("calls/start/", CallStartAPI.as_view(), name="call_start"),
    path("calls/<int:session_id>/ivr/", IVRInputAPI.as_view(), name="ivr_input"),
    path("calls/<int:session_id>/followup/", FollowUpAPI.as_view(), name="call_followup"),
]
