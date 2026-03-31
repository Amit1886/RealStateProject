from django.urls import path
from realstateproject.lazy_views import lazy_view

app_name = "voice"

urlpatterns = [
    path("", lazy_view("voice.views.voice_dashboard"), name="dashboard"),
]
