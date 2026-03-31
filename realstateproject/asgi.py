"""
ASGI config for khatapro project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "realstateproject.settings")

django_asgi_app = get_asgi_application()

try:
    import chatbot.routing  # noqa: E402
    chatbot_patterns = chatbot.routing.websocket_urlpatterns
except Exception:
    chatbot_patterns = []

try:
    import realtime.routing  # noqa: E402
    realtime_patterns = realtime.routing.websocket_urlpatterns
except Exception:
    realtime_patterns = []

websocket_urlpatterns = chatbot_patterns + realtime_patterns

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)
