"""
ASGI config for textcollab_project project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "textcollab_project.settings")
django_asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack
from channels.routing import ChannelNameRouter, ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

import textcollab.routing
from channels_yroom.channel import YRoomChannelConsumer


application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(textcollab.routing.websocket_urlpatterns))
        ),
        "channel": ChannelNameRouter(
            {
                "yroom": YRoomChannelConsumer.as_asgi(),
            }
        ),
    }
)
