import logging
import random
from typing import Optional

from channels.generic.websocket import AsyncWebsocketConsumer

from .conf import settings
from .utils import (
    YroomChannelMessage,
    YroomChannelMessageType,
    YroomChannelResponse,
    get_connection_group_name,
)

logger = logging.getLogger(__name__)


class YRoomConsumerHooks:
    async def pre_connect(self):
        pass

    async def post_connect(self):
        pass

    async def pre_disconnect(self):
        pass

    async def post_disconnect(self):
        pass

    async def pre_receive(self, text_data: Optional[str] = None, bytes_data: Optional[bytes] = None
    ) -> None:
        pass

    async def post_receive(self, text_data: Optional[str] = None, bytes_data: Optional[bytes] = None
    ) -> None:
        pass

class YroomConsumer(AsyncWebsocketConsumer, YRoomConsumerHooks):
    room_name_prefix: str = "yroom"
    room_url_kwargs: str | None = None


    def get_room_group_name(self) -> str:
        room_name = "default"
        if self.room_url_kwargs is not None:
            room_name = self.scope["url_route"]["kwargs"][self.room_url_kwargs]
        return f"{self.room_name_prefix}_{room_name}"

    def get_connection_id(self) -> int:
        return random.getrandbits(64)

    async def connect(self) -> None:
        await self.pre_connect() # Hook
        await self.join_room()
        await self.post_connect() # Hook

    async def join_room(self) -> None:
        # Join room group
        self.room_group_name = self.get_room_group_name()
        self.conn_id = self.get_connection_id()

        logger.debug("joining room %s as %s", self.room_group_name, self.conn_id)
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        conn_group_name = get_connection_group_name(self.conn_id)
        await self.channel_layer.group_add(conn_group_name, self.channel_name)
        await self.accept()
        await self.channel_layer.send(
            settings.YROOM_CHANNEL_NAME,
            YroomChannelMessage(
                type=YroomChannelMessageType.connect.value,
                room=self.room_group_name,
                conn_id=self.conn_id,
            ),
        )

    async def disconnect(self, close_code) -> None:
        await self.pre_disconnect() # Hook
        await self.leave_room()
        await self.post_disconnect() # Hook

    async def leave_room(self) -> None:
        # Leave room group
        logger.debug("leaving room %s as %s", self.room_group_name, self.conn_id)
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        conn_group_name = get_connection_group_name(self.conn_id)
        await self.channel_layer.group_discard(conn_group_name, self.channel_name)
        # Tell yroom worker that client disconnected
        await self.channel_layer.send(
            settings.YROOM_CHANNEL_NAME,
            YroomChannelMessage(
                type=YroomChannelMessageType.disconnect.value,
                room=self.room_group_name,
                conn_id=self.conn_id,
            ),
        )

    async def receive(
        self, text_data: Optional[str] = None, bytes_data: Optional[bytes] = None
    ) -> None:
        await self.pre_receive(text_data, bytes_data) # Hook
        # Receive message from WebSocket
        if bytes_data:
            await self.handle_room_message(bytes_data)
        await self.post_receive(text_data, bytes_data) # Hook

    async def handle_room_message(self, bytes_data: bytes) -> None:
        await self.channel_layer.send(
            settings.YROOM_CHANNEL_NAME,
            YroomChannelMessage(
                type=YroomChannelMessageType.message.value,
                room=self.room_group_name,
                conn_id=self.conn_id,
                payload=bytes_data,
            ),
        )

    async def forward_payload(self, message: YroomChannelResponse) -> None:
        await self.send(bytes_data=message["payload"])
