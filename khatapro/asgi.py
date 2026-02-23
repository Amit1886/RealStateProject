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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "khatapro.settings")

django_asgi_app = get_asgi_application()

import chatbot.routing  # noqa: E402
import realtime.routing  # noqa: E402
import system_mode.routing  # noqa: E402

websocket_urlpatterns = (
    chatbot.routing.websocket_urlpatterns
    + system_mode.routing.websocket_urlpatterns
    + realtime.routing.websocket_urlpatterns
)

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)
