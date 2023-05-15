import asyncio
from io import StringIO

import pytest
from channels.layers import get_channel_layer
from channels.routing import ChannelNameRouter, ProtocolTypeRouter
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

    application = ProtocolTypeRouter(
        {
            "channel": ChannelNameRouter(
                {
                    "yroom": YRoomChannelConsumer.as_asgi(),
                }
            ),
        }
    )

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

    worker = YroomWorker(
        channel=channel, channel_layer=channel_layer, application=application
    )
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
    await worker.shutdown_worker(FakeSignal, fake_loop)
    assert loop_state["stopped"]
    assert fake_loop.removed_signals == set(worker.SIGNALS)

    ydoc_update = await YDocUpdate.objects.aget(name=room_name)
    assert ydoc_update.timestamp > timestamp_before

    worker_task.cancel()
    try:
        await worker_task
    except asyncio.exceptions.CancelledError:
        pass
