import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

from channels.consumer import AsyncConsumer
from yroom import YRoomManager, YRoomMessage

from .conf import get_room_prefix, get_room_settings, get_settings
from .storage import YDocStorage, get_ydoc_storage
from .utils import YroomChannelMessage, YroomChannelRPCMessage

logger = logging.getLogger(__name__)


class YRoomChannelConsumer(AsyncConsumer):
    def __init__(self) -> None:
        self.room_manager: YRoomManager = YRoomManager(get_settings())
        self.cleanup_tasks = {}
        self.storages: dict[str, YDocStorage] = {}

    def get_storage(self, room_name):
        prefix = get_room_prefix(room_name)
        if prefix in self.storages:
            return self.storages[prefix]
        storage = get_ydoc_storage(room_name)
        self.storages[prefix] = storage
        return storage

    async def connect(self, message: YroomChannelMessage) -> None:
        room_name = message["room"]
        conn_id = message["conn_id"]
        logger.debug("yroom consumer connect %s %s", room_name, conn_id)

        # Cancel room cleanup task if it exists
        if room_name in self.cleanup_tasks:
            self.cleanup_tasks[room_name].cancel()

        result = None
        if not self.room_manager.has_room(room_name):
            result = await self.create_room_from_snapshot(room_name, conn_id)
        if result is None:
            logger.debug(
                "yroom connect, room present or no snapshot %s %s", room_name, conn_id
            )
            result = self.room_manager.connect(room_name, conn_id)
        await self.respond(
            result, room_name=room_name, channel_name=message["channel_name"]
        )

    async def create_room_from_snapshot(
        self, room_name: str, conn_id: int = 0
    ) -> Optional[YRoomMessage]:
        logger.debug("yroom connect, no room yet %s %s", room_name, conn_id)
        storage = self.get_storage(room_name)
        logger.debug("Using yroom storage %s of %s", storage, self.storages)
        snapshot = bytes(await storage.get_snapshot(room_name))
        logger.debug("Found snapshot %s", snapshot)
        if snapshot:
            logger.debug("yroom connect, snapshot found %s %s", room_name, snapshot)
            return self.room_manager.connect_with_data(room_name, conn_id, snapshot)

    async def message(self, message: YroomChannelMessage) -> None:
        room_name = message["room"]
        conn_id = message["conn_id"]
        channel_name = message["channel_name"]
        logger.debug("yroom consumer message %s %s: %s", room_name, conn_id, message)
        # If room not present (and connect is lost/expired?), try restore first
        if not self.room_manager.has_room(room_name):
            # Ignore result, connect is kind of optional
            await self.create_room_from_snapshot(room_name, conn_id)
        result = self.room_manager.handle_message(
            room_name, conn_id, message["payload"]
        )
        await self.respond(result, room_name=room_name, channel_name=channel_name)

    @asynccontextmanager
    async def try_room(self, room_name: str) -> None:
        try:
            has_room = True
            if not self.room_manager.has_room(room_name):
                has_room = False
                result = await self.create_room_from_snapshot(room_name)
                has_snapshot = result is not None
            yield has_room or has_snapshot
        finally:
            if not has_room:
                # if room was not present before, disconnect client, remove room
                await self.disconnect_client(room_name, send_response=False)

    async def rpc(self, message: YroomChannelRPCMessage) -> None:
        room_name = message["room"]
        method = message["method"]
        if not hasattr(self.room_manager, method):
            logger.warning("yroom consumer bad rpc method %s %s", room_name, method)
            return
        manager_method = getattr(self.room_manager, method)
        if not callable(manager_method):
            logger.warning("yroom consumer bad rpc method %s %s", room_name, method)
            return
        logger.debug("yroom consumer rpc %s %s", room_name, method)
        async with self.try_room(room_name) as room_available:
            if not room_available:
                # No room and no snapshot, send back empty result
                await self.channel_layer.send(
                    message["channel_name"],
                    {
                        "type": "rpc_response",
                        "result": None,
                    },
                )
                return
            result = manager_method(room_name, *message["params"])
        logger.debug(
            "yroom consumer rpc response %s %s to %s: %s",
            room_name,
            method,
            message["channel_name"],
            result,
        )
        await self.channel_layer.send(
            message["channel_name"],
            {
                "type": "rpc_response",
                "result": result,
            },
        )

    async def respond(
        self,
        result: YRoomMessage,
        room_name: str,
        channel_name: Optional[str] = None,
    ) -> None:
        logger.debug(
            "yroom response in room %s at channel %s (client: %s, broadcast: %s)",
            room_name,
            channel_name,
            result.payloads,
            result.broadcast_payloads,
        )
        if result.payloads and channel_name:
            await self.channel_layer.send(
                channel_name,
                {"type": "forward_payload", "payloads": result.payloads},
            )
        if result.broadcast_payloads:
            await self.channel_layer.group_send(
                room_name,
                {"type": "forward_payload", "payloads": result.broadcast_payloads},
            )

    async def disconnect(self, message: YroomChannelMessage) -> None:
        await self.disconnect_client(message["room"], conn_id=message["conn_id"])

    async def disconnect_client(
        self, room_name: str, conn_id: int = 0, send_response: bool = True
    ) -> None:
        if not self.room_manager.has_room(room_name):
            # We don't know this room, disconnect invalid
            return
        logger.debug("yroom consumer disconnect %s %s", room_name, conn_id)
        result = self.room_manager.disconnect(room_name, conn_id)
        if not self.room_manager.is_room_alive(room_name):
            logger.debug("Room %s is empty", room_name)
            await self.schedule_room_removal(room_name)
        if send_response:
            await self.respond(result, room_name=room_name, channel_name=None)

    async def schedule_room_removal(self, room_name: str):
        if room_name in self.cleanup_tasks:
            self.cleanup_tasks[room_name].cancel()

        task = asyncio.create_task(self.remove_room_soon(room_name))
        self.cleanup_tasks[room_name] = task
        task.add_done_callback(lambda _task: self.cleanup_tasks.pop(room_name, None))

    async def remove_room_soon(self, room_name: str):
        # Wait a bit and then check if the room is still alive
        room_settings = get_room_settings(room_name)
        await asyncio.sleep(room_settings["REMOVE_ROOM_DELAY"])
        await self.remove_room(room_name)

    async def remove_room(self, room_name: str):
        if self.room_manager.is_room_alive(room_name):
            return
        logger.debug("Snapshot room %s", room_name)
        await self.snapshot_room(room_name)
        logger.debug("Remove empty room %s", room_name)
        if not self.room_manager.is_room_alive(room_name):
            self.force_remove_room(room_name)

    def force_remove_room(self, room_name: str):
        self.room_manager.remove_room(room_name)

    async def snapshot_room(self, room_name: str):
        ydoc_bytes = self.room_manager.serialize_room(room_name)
        logger.debug(
            "Snapshot room %s with %s bytes", room_name, len(ydoc_bytes or b"")
        )
        if ydoc_bytes is None:
            # Room is gone!
            return
        storage = self.get_storage(room_name)
        await storage.save_snapshot(room_name, ydoc_bytes)

    async def shutdown(self, message) -> None:
        logger.info("Shutdown event received")
        cleanup_tasks = list(self.cleanup_tasks.values())
        for task in cleanup_tasks:
            task.cancel()
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        self.cleanup_tasks = {}
        logger.debug("Cleaned up tasks")
        for room_name in self.room_manager.list_rooms():
            logger.debug("Saving snapshot for %s", room_name)
            await self.snapshot_room(room_name)
        logger.debug("Done saving snapshots")
        await self.send({"type": "shutdown.complete"})
