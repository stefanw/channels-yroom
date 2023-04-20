import json
from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict

from channels.layers import get_channel_layer
from django.conf import settings


class YroomChannelResponse(TypedDict):
    type: str
    payload: bytes


class YroomChannelMessageType(str, Enum):
    connect = "connect"
    disconnect = "disconnect"
    message = "message"
    rpc = "rpc"


class _YroomChannelMessage(TypedDict):  # implicitly total=True
    type: YroomChannelMessageType
    room: str
    conn_id: int


class YroomChannelMessage(_YroomChannelMessage, total=False):
    payload: bytes


class YroomChannelRPCMessage(TypedDict):
    type: str
    room: str
    channel: str
    method: str
    params: List[Any]


class YroomChannelRPCResponse(TypedDict):
    type: str
    result: Any


def get_connection_group_name(conn_id) -> str:
    return "yroom-connection_%s" % conn_id


class YroomDocument:
    def __init__(self, room_name: str, channel_layer=None) -> None:
        self.room_name = room_name
        if channel_layer is None:
            self.channel_layer = get_channel_layer()

    async def get_map(self, name: str) -> Optional[Dict[str, Any]]:
        return await self._send_json_rpc("get_map", [name])

    async def get_array(self, name: str) -> Optional[List[Any]]:
        return await self._send_json_rpc("get_array", [name])

    async def get_xml_fragment(self, name: str) -> Optional[str]:
        return await self._send_rpc("get_xml_fragment", [name])

    async def get_text(self, name: str) -> Optional[str]:
        return await self._send_rpc("get_text", [name])

    async def get_xml_element(self, name: str) -> Optional[str]:
        return await self._send_rpc("get_xml_element", [name])

    async def get_xml_text(self, name: str) -> Optional[str]:
        return await self._send_rpc("get_xml_text", [name])

    async def _send_json_rpc(self, method: str, params: List[Any]) -> Optional[Any]:
        data = await self._send_rpc("get_map", params)
        if data is None:
            return None
        return json.loads(data)

    async def _send_rpc(self, method: str, params: List[Any]) -> Any:
        channel_name: str = await self.channel_layer.new_channel()
        await self.channel_layer.send(
            settings.YROOM_CHANNEL_NAME,
            YroomChannelRPCMessage(
                type=YroomChannelMessageType.rpc.value,
                room=self.room_name,
                channel=channel_name,
                method=method,
                params=params,
            ),
        )
        response: YroomChannelRPCResponse = await self.channel_layer.receive(
            channel_name
        )
        return response["result"]
