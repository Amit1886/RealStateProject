from django.urls import re_path

from .consumers import StreamConsumer

websocket_urlpatterns = [
    re_path(r"ws/realtime/(?P<stream_name>[a-z_]+)/$", StreamConsumer.as_asgi()),
]
