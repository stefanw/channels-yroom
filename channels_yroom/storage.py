from typing import Optional, Protocol

from asgiref.sync import sync_to_async
from django.utils.module_loading import import_string

from .conf import get_room_settings
from .models import YDocUpdate


class YDocStorage(Protocol):
    async def get_snapshot(self, name: str) -> Optional[bytes]:
        ...

    async def save_snapshot(self, name: str, data: bytes) -> None:
        ...


class YDocDummyStorage(YDocStorage):
    async def get_snapshot(self, name: str) -> Optional[bytes]:
        return None

    async def save_snapshot(self, name: str, data: bytes) -> None:
        pass


class YDocMemoryStorage(YDocStorage):
    def __init__(self):
        self._snapshots = {}

    async def get_snapshot(self, name: str) -> Optional[bytes]:
        return self._snapshots.get(name)

    async def save_snapshot(self, name: str, data: bytes) -> None:
        self._snapshots[name] = data


@sync_to_async
def get_db_snapshot(room_name: str):
    return YDocUpdate.objects.get_snapshot(room_name)


@sync_to_async
def save_db_snapshot(room_name: str, data: bytes):
    return YDocUpdate.objects.save_snapshot(room_name, data)


class YDocDatabaseStorage(YDocStorage):
    async def get_snapshot(self, name: str) -> Optional[bytes]:
        return await get_db_snapshot(name)

    async def save_snapshot(self, name: str, data: bytes) -> None:
        await save_db_snapshot(name, data)


storage_cache = {}


def get_ydoc_storage(room_name) -> YDocStorage:
    room_settings = get_room_settings(room_name)
    backend = room_settings["STORAGE_BACKEND"]
    if backend in storage_cache:
        return storage_cache[backend]
    storage = import_string(backend)()
    storage_cache[backend] = storage
    return storage
