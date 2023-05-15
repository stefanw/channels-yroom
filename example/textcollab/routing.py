from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(
        r"ws/prosemirror/(?P<room_name>\w+)$", consumers.TextCollabConsumer.as_asgi()
    ),
    re_path(r"ws/tiptap/(?P<room_name>\w+)$", consumers.TipTapConsumer.as_asgi()),
]
