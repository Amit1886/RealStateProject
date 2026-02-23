from django.urls import re_path

from .consumers import SystemModeConsumer


websocket_urlpatterns = [
    re_path(r"ws/system-mode/$", SystemModeConsumer.as_asgi()),
]
