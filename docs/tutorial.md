# Getting started

## Adding real-time collaboration to your Django project

This tutorial assumes that you have tried out the [Channels tutorial](https://channels.readthedocs.io/en/stable/tutorial/index.html) (at least part 1 and 3).

### Install

```
pip install channels-yroom
```

### Add apps to settings

Add `"channels"` and `"channels_yroom"` to `INSTALLED_APPS` in your settings.

### Setup consumer

Set up your WebSocket consumer in your app `consumers.py`.

```python
from channels_yroom.consumer import YroomConsumer

class TextCollaborationConsumer(YroomConsumer):
    def get_room_group_name(self) -> str:
        """
        Determine a unique name for this room, e.g. based on URL
        """
        room_name = self.scope["url_route"]["kwargs"]["room_name"]
        return "textcollab.%s" % room_name

    async def connect(self) -> None:
        """
        Optional: perform some sort of authentication
        """
        user = self.scope["user"]
        if not user.is_staff:
            await self.close()
            return

        await super().connect()
```

### Configure protocols in asgi.py

Hook your WebSocket patterns in your `asgi.py` and add a `"channel"` protocol router for the `"yroom"` channel name:

```python
# ...
application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
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
```

### Run yroom worker process

In addition to your webserver with WebSockets support (e.g. daphne or uvicorn), you need to run a [channels worker](https://channels.readthedocs.io/en/stable/topics/worker.html). You can run the `yroom` worker implementation that supports graceful shutdown:

```sh
python manage.py yroom
```