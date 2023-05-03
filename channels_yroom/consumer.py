import logging
import random
from typing import Optional

from channels.generic.websocket import AsyncWebsocketConsumer

from .conf import get_room_settings
from .utils import (
    YroomChannelMessage,
    YroomChannelMessageType,
    YroomChannelResponse,
    get_connection_group_name,
)

logger = logging.getLogger(__name__)


class YroomConsumer(AsyncWebsocketConsumer):
    room_name = "yroom_default"

    def get_room_name(self) -> str:
        """Returns the name of the room group to join.
            This represents the room that the client is joining.

        Returns:
            str: room group name
        """
        return self.room_name

    def get_connection_id(self) -> int:
        return random.getrandbits(64)

    async def connect(self) -> None:
        """
        Called when the websocket is handshaking as part of initial connection.
        Override and perform authentication here (see
        [Channels documentation on AsyncWebsocketConsumer](https://channels.readthedocs.io/en/stable/topics/consumers.html#asyncwebsocketconsumer)).

        Call either `await self.join_room()` to accept the connection (default implementation)
        or `await self.close()` to reject.

        """  # noqa: E501
        await self.join_room()

    async def join_room(self) -> None:
        # Join room group
        self.room_name = self.get_room_name()
        self.conn_id = self.get_connection_id()

        logger.debug("joining room %s as %s", self.room_name, self.conn_id)
        await self.channel_layer.group_add(self.room_name, self.channel_name)
        conn_group_name = get_connection_group_name(self.conn_id)
        await self.channel_layer.group_add(conn_group_name, self.channel_name)
        await self.accept()
        self.room_settings = get_room_settings(self.room_name)
        await self.channel_layer.send(
            self.room_settings["CHANNEL_NAME"],
            YroomChannelMessage(
                type=YroomChannelMessageType.connect.value,
                room=self.room_name,
                conn_id=self.conn_id,
            ),
        )

    async def disconnect(self, close_code) -> None:
        await self.leave_room()

    async def leave_room(self) -> None:
        # Leave room group
        logger.debug("leaving room %s as %s", self.room_name, self.conn_id)
        await self.channel_layer.group_discard(self.room_name, self.channel_name)
        conn_group_name = get_connection_group_name(self.conn_id)
        await self.channel_layer.group_discard(conn_group_name, self.channel_name)
        # Tell yroom worker that client disconnected
        await self.channel_layer.send(
            self.room_settings["CHANNEL_NAME"],
            YroomChannelMessage(
                type=YroomChannelMessageType.disconnect.value,
                room=self.room_name,
                conn_id=self.conn_id,
            ),
        )

    async def receive(
        self, text_data: Optional[str] = None, bytes_data: Optional[bytes] = None
    ) -> None:
        # Receive message from WebSocket
        if bytes_data:
            await self.handle_room_message(bytes_data)

    async def handle_room_message(self, bytes_data: bytes) -> None:
        await self.channel_layer.send(
            self.room_settings["CHANNEL_NAME"],
            YroomChannelMessage(
                type=YroomChannelMessageType.message.value,
                room=self.room_name,
                conn_id=self.conn_id,
                payload=bytes_data,
            ),
        )

    async def forward_payload(self, message: YroomChannelResponse) -> None:
        await self.send(bytes_data=message["payload"])
