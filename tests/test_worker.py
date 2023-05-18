import asyncio
from io import StringIO

import pytest
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.core.management import call_command

from channels_yroom.channel import YRoomChannelConsumer
from channels_yroom.conf import get_default_room_settings
from channels_yroom.consumer import YroomConsumer
from channels_yroom.management.commands.yroom import Command as YroomCommand
from channels_yroom.models import YDocUpdate
from channels_yroom.storage import get_ydoc_storage
from channels_yroom.worker import YroomWorker


def test_yroom_command(monkeypatch):
    class FakeWorker:
        def __init__(self, channel, channel_layer):
            self.channel = channel
            self.channel_layer = channel_layer

        def run(self):
            pass

    monkeypatch.setattr(YroomCommand, "worker_class", FakeWorker)
    out = StringIO()
    call_command(
        "yroom",
        stdout=out,
        stderr=StringIO(),
    )
    assert "Running worker for channel 'yroom'\n" == out.getvalue()

    out = StringIO()
    call_command(
        "yroom",
        "--channel",
        "foobar",
        stdout=out,
        stderr=StringIO(),
    )
    assert "Running worker for channel 'foobar'\n" == out.getvalue()


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_yroom_worker(settings, ydata):
    settings.YROOM_SETTINGS = {
        "default": {
            "STORAGE_BACKEND": "channels_yroom.storage.YDocDatabaseStorage",
            "REMOVE_ROOM_DELAY": 0,
        }
    }

    channel_layer = get_channel_layer()
    channel = get_default_room_settings()["CHANNEL_NAME"]

    loop_state = {}

    class FakeSignal:
        name = "FakeSignal"

    class FakeLoop:
        removed_signals = set()
        added_signals = set()

        def add_signal_handler(self, sig, callback):
            self.added_signals.add(sig)

        def remove_signal_handler(self, sig):
            self.removed_signals.add(sig)

        def stop(self):
            loop_state["stopped"] = True

    fake_loop = FakeLoop()

    worker = YroomWorker(channel=channel, channel_layer=channel_layer)
    worker._setup_signal_handlers(fake_loop)
    assert fake_loop.added_signals == set(worker.SIGNALS)
    worker_task = asyncio.create_task(worker.run_worker())

    app = YroomConsumer()
    room_name = app.get_room_name()

    storage = get_ydoc_storage(room_name)
    await storage.save_snapshot(room_name, ydata.DOC_DATA)
    ydoc_update = await YDocUpdate.objects.aget(name=room_name)
    timestamp_before = ydoc_update.timestamp

    client_1 = WebsocketCommunicator(app, "/testws/")
    connected, _ = await client_1.connect()
    assert connected

    payload = await client_1.receive_from()
    assert payload == ydata.SYNC_STEP_1_DATA

    fake_loop = FakeLoop()
    await worker.shutdown_worker(fake_loop, FakeSignal)
    assert loop_state["stopped"]
    assert fake_loop.removed_signals == set(worker.SIGNALS)

    ydoc_update = await YDocUpdate.objects.aget(name=room_name)
    assert ydoc_update.timestamp > timestamp_before

    worker_task.cancel()
    try:
        await worker_task
    except asyncio.exceptions.CancelledError:
        pass


@pytest.mark.django_db
def test_worker_exception_handling(event_loop, capsys):
    channel_layer = get_channel_layer()
    channel = get_default_room_settings()["CHANNEL_NAME"]

    channel_state = {"shutdown_called": False}

    class TestException(Exception):
        pass

    class TestYroomChannelConsumer(YRoomChannelConsumer):
        async def connect(self, message):
            await super().connect(message)
            raise TestException("Test exception")

        async def shutdown(self, message):
            channel_state["shutdown_called"] = True
            await super().shutdown(message)

    class TestYroomWorker(YroomWorker):
        consumer_class = TestYroomChannelConsumer

    worker = TestYroomWorker(channel=channel, channel_layer=channel_layer)
    event_loop.set_exception_handler(worker.handle_exception)

    app = YroomConsumer()
    client_1 = WebsocketCommunicator(app, "/testws/")

    async def connect_client():
        connected, _ = await client_1.connect()
        assert connected

    event_loop.create_task(worker.run_worker())
    event_loop.create_task(connect_client())
    event_loop.run_forever()
    event_loop.close()

    captured = capsys.readouterr()
    assert 'raise TestException("Test exception")' in captured.err
    assert channel_state["shutdown_called"]
    assert worker.shutting_down
    assert event_loop.is_closed()


@pytest.mark.django_db
def test_worker_exception_handling_during_shutdown(event_loop, capsys, caplog):
    channel_layer = get_channel_layer()
    channel = get_default_room_settings()["CHANNEL_NAME"]

    class TestException(Exception):
        pass

    class TestShutdownException(Exception):
        pass

    class TestYroomChannelConsumer(YRoomChannelConsumer):
        async def connect(self, message):
            await super().connect(message)
            raise TestException("Test exception")

        async def shutdown(self, message):
            raise TestShutdownException("Test shutdown exception")

    class TestYroomWorker(YroomWorker):
        consumer_class = TestYroomChannelConsumer

    worker = TestYroomWorker(channel=channel, channel_layer=channel_layer)
    event_loop.set_exception_handler(worker.handle_exception)

    app = YroomConsumer()
    client_1 = WebsocketCommunicator(app, "/testws/")

    async def connect_client():
        connected, _ = await client_1.connect()
        assert connected

    event_loop.create_task(worker.run_worker())
    event_loop.create_task(connect_client())
    event_loop.run_forever()
    event_loop.close()

    captured = capsys.readouterr()
    log_messages = [rec.message for rec in caplog.records]
    assert 'raise TestException("Test exception")' in captured.err
    assert (
        "Caught exception while shutting down: Test shutdown exception" in log_messages
    )

    assert worker.shutting_down
    assert event_loop.is_closed()
