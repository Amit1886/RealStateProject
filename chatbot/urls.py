from django.urls import path
from .views import chatbot_reply

urlpatterns = [
    path("reply/", chatbot_reply, name="chatbot_reply"),
]
