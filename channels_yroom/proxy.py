import json
from typing import Any, Dict, List

from channels.layers import get_channel_layer

from .conf import get_room_settings
from .utils import (
    YroomChannelMessageType,
    YroomChannelRPCMessage,
    YroomChannelRPCResponse,
)


class DataUnavailable(LookupError):
    pass


class YroomDocument:
    """
    A proxy object for a Ydoc in the yroom process
    that allows to export all Ytypes.

    """

    def __init__(self, room_name: str, channel_layer=None) -> None:
        """Instantiate a YroomDocument.

        Args:
            room_name (str): the room group name chosen by the consumer
            channel_layer (optional): A channel layer. Defaults to default
                channel layer.
        """
        self.room_name = room_name
        if channel_layer is None:
            self.channel_layer = get_channel_layer()

    async def export_map(self, name: str) -> Dict[str, Any]:
        """Get an export of a Ymap as a Python dictionary.
        Raises DataUnavailable if the map is not present in the Ydoc
            or the room is not present and cannot be restored from storage.

        Args:
            name (str): name of the map

        Returns:
            Dict[str, Any]: A dictionary representing the exported map
        """
        return await self._export_type_json("get_map", name)

    async def export_array(self, name: str) -> List[Any]:
        return await self._export_type_json("get_array", name)

    async def export_xml_fragment(self, name: str) -> str:
        return await self._export_type("get_xml_fragment", name)

    async def export_text(self, name: str) -> str:
        return await self._export_type("get_text", name)

    async def export_xml_element(self, name: str) -> str:
        return await self._export_type("get_xml_element", name)

    async def export_xml_text(self, name: str) -> str:
        return await self._export_type("get_xml_text", name)

    async def _export_type_json(self, method: str, name: str) -> Any:
        data = await self._export_type(method, name)
        return json.loads(data)

    async def _export_type(self, method: str, name: str) -> Any:
        result = await self._send_rpc(method, [name])
        if result is None:
            raise DataUnavailable(name)
        return result

    async def _send_rpc(self, method: str, params: List[Any]) -> Any:
        channel_name: str = await self.channel_layer.new_channel()
        room_settings = get_room_settings(self.room_name)
        await self.channel_layer.send(
            room_settings["CHANNEL_NAME"],
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
