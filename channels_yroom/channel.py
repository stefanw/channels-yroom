import asyncio
import logging

from channels.consumer import AsyncConsumer
from yroom import YRoomManager, YRoomMessage

from .conf import settings
from .storage import get_ydoc_storage, YDocStorage
from .utils import YroomChannelMessage, get_connection_group_name

logger = logging.getLogger(__name__)


class YRoomChannelConsumer(AsyncConsumer):
    def __init__(self) -> None:
        self.room_manager: YRoomManager = YRoomManager()
        self.storage: YDocStorage = get_ydoc_storage()
        self.cleanup_tasks = {}

    async def connect(self, message: YroomChannelMessage) -> None:
        room_name = message["room"]
        conn_id = message["conn_id"]
        logger.debug("yroom consumer connect %s %s", room_name, conn_id)
        result = None
        if not self.room_manager.has_room(room_name):
            snapshot = await self.storage.get_snapshot(room_name)
            if snapshot:
                result = self.room_manager.connect_with_data(
                    room_name, conn_id, snapshot
                )
        if result is None:
            result = self.room_manager.connect(room_name, conn_id)
        await self.respond(conn_id, room_name, result)

    async def message(self, message: YroomChannelMessage) -> None:
        room_name = message["room"]
        conn_id = message["conn_id"]
        # logger.debug("yroom consumer message %s %s", room_name, conn_id)
        result = self.room_manager.handle_message(
            room_name, conn_id, message["payload"]
        )
        await self.respond(conn_id, room_name, result)

    async def respond(self, conn_id: int, room_name: str, result: YRoomMessage) -> None:
        # logger.debug(
        #     "yroom response in room %s at conection %s (client: %s, broadcast: %s)",
        #     room_name,
        #     conn_id,
        #     bool(result.payload),
        #     bool(result.broadcast_payload),
        # )
        if result.payload:
            conn_group_name = get_connection_group_name(conn_id)
            await self.send_response(conn_group_name, result.payload)
        if result.broadcast_payload:
            await self.send_response(room_name, result.broadcast_payload)

    async def send_response(self, group_name: str, payload: bytes) -> None:
        await self.channel_layer.group_send(
            group_name,
            {"type": "forward_payload", "payload": payload},
        )

    async def disconnect(self, message: YroomChannelMessage) -> None:
        room_name = message["room"]
        conn_id = message["conn_id"]
        logger.debug("yroom consumer disconnect %s %s", room_name, conn_id)
        result = self.room_manager.disconnect(room_name, conn_id)
        if not self.room_manager.is_room_alive(room_name):
            logger.debug("Room %s is dead", room_name)
            await self.schedule_room_removal(room_name)
        await self.respond(conn_id, room_name, result)

    async def schedule_room_removal(self, room_name: str):
        if room_name in self.cleanup_tasks:
            self.cleanup_tasks[room_name].cancel()

        task = asyncio.create_task(self.remove_room_soon(room_name))
        self.cleanup_tasks[room_name] = task
        task.add_done_callback(lambda _task: self.cleanup_tasks.pop(room_name, None))

    async def remove_room_soon(self, room_name: str):
        # Wait a bit and then check if the room is still alive
        await asyncio.sleep(settings.YROOM_REMOVE_ROOM_DELAY)
        await self.remove_room(room_name)

    async def remove_room(self, room_name: str):
        if self.room_manager.is_room_alive(room_name):
            return
        logger.debug("Snapshot room %s", room_name)
        await self.snapshot_room(room_name)
        logger.debug("Remove dead room %s", room_name)
        if not self.room_manager.is_room_alive(room_name):
            self.force_remove_room(room_name)

    def force_remove_room(self, room_name: str):
        self.room_manager.remove_room(room_name)

    async def snapshot_room(self, room_name: str):
        ydoc_bytes = self.room_manager.serialize_room(room_name)
        if ydoc_bytes is None:
            # Room is gone!
            return
        await self.storage.save_snapshot(room_name, ydoc_bytes)

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
            snapshot = self.room_manager.serialize_room(room_name)
            await self.storage.save_snapshot(room_name, snapshot)
        logger.debug("Done saving snapshots")
        await self.send({"type": "shutdown.complete"})
