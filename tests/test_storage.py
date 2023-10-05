import pytest

from channels_yroom.models import YDocUpdate
from channels_yroom.storage import (
    YDocDatabaseStorage,
    YDocMemoryStorage,
    get_ydoc_storage,
)


@pytest.mark.asyncio
async def test_memory_storage(settings):
    settings.YROOM_SETTINGS = {
        "default": {
            "STORAGE_BACKEND": "channels_yroom.storage.YDocMemoryStorage",
        }
    }
    storage = get_ydoc_storage("test")
    assert isinstance(storage, YDocMemoryStorage)
    assert await storage.get_snapshot("test") is None
    await storage.save_snapshot("test", b"test") is None
    assert await storage.get_snapshot("test") == b"test"


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_database_storage(settings):
    settings.YROOM_SETTINGS = {
        "default": {
            "STORAGE_BACKEND": "channels_yroom.storage.YDocDatabaseStorage",
        }
    }
    storage = get_ydoc_storage("test")
    assert isinstance(storage, YDocDatabaseStorage)
    assert await storage.get_snapshot("test") is None
    await storage.save_snapshot("test", b"test") is None
    assert await storage.get_snapshot("test") == b"test"


@pytest.mark.django_db(transaction=True)
def test_database_storage_model(settings):
    assert YDocUpdate.objects.all().count() == 0

    upd, created = YDocUpdate.objects.save_snapshot("test", b"test")
    assert created is True
    assert str(upd) == "test"
    assert upd.data == b"test"
    upd, created = YDocUpdate.objects.save_snapshot("test", b"test2")
    assert created is False
    assert str(upd) == "test"
    assert upd.data == b"test2"
    assert YDocUpdate.objects.get_snapshot("test") == b"test2"
    assert YDocUpdate.objects.get_snapshot("not-there") is None
