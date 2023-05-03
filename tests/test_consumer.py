import asyncio
from collections import deque
from contextlib import asynccontextmanager

import pytest
import pytest_asyncio
import y_py as Y
from asgiref.testing import ApplicationCommunicator
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator

from channels_yroom.channel import YRoomChannelConsumer
from channels_yroom.conf import get_room_settings
from channels_yroom.consumer import YroomConsumer
from channels_yroom.models import YDocUpdate
from channels_yroom.proxy import DataUnavailable, YroomDocument
from channels_yroom.storage import get_ydoc_storage


class FakeWorker:
    def __init__(self, channel_layer, channel, worker_communicator):
        self.channel_layer = channel_layer
        self.channel = channel
        self.worker_communicator = worker_communicator
        self.messages = deque()

    @classmethod
    def from_defaults(
        cls, room_name="yroom_default", channel_consumer_class=YRoomChannelConsumer
    ):
        channel_consumer = channel_consumer_class()
        room_settings = get_room_settings(room_name)
        channel_layer = get_channel_layer()
        channel = room_settings["CHANNEL_NAME"]

        worker_communicator = ApplicationCommunicator(
            channel_consumer, {"type": "channel", "channel": channel}
        )
        return cls(channel_layer, channel, worker_communicator)

    async def run_fake_worker(self):
        self.event = asyncio.Event()
        while True:
            # Receive message on channel layer...
            message = await self.channel_layer.receive(self.channel)
            self.messages.appendleft(message)
            # ... and give it to worker consumer
            await self.worker_communicator.send_input(message)
            self.event.set()

    async def wait_for_message(self):
        if not self.messages:
            await self.event.wait()
            self.event = asyncio.Event()
        message = self.messages.pop()
        return message

    async def shutdown(self):
        communicator = self.worker_communicator
        await communicator.send_input({"type": "shutdown", "signal": "SIGTERM"})
        shutdown_confirmation = await communicator.receive_output(1)
        assert shutdown_confirmation["type"] == "shutdown.complete"

    @asynccontextmanager
    async def start(self):
        task = asyncio.create_task(self.run_fake_worker())
        yield
        await self.worker_communicator.wait()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


@pytest_asyncio.fixture(scope="function")
async def yroom_worker():
    worker_runner = FakeWorker.from_defaults()
    async with worker_runner.start():
        yield worker_runner


@pytest.mark.asyncio
async def test_yroom_consumer():
    worker_results = {}

    class TestConsumer(YroomConsumer):
        pass

    class TestYRoomChannelConsumer(YRoomChannelConsumer):
        async def shutdown(self, message):
            worker_results["shutdown"] = True
            await super().shutdown(message)

    SYNC_STEP_1 = b"\x00\x00\x01\x00"
    SYNC_STEP_2 = b"\x00\x01\x02\x00\x00"
    AWARENESS_UPDATE = b"\x01\x01\x00"

    app = TestConsumer()
    app_2 = TestConsumer()
    room_name = app.get_room_name()

    fake_worker = FakeWorker.from_defaults(
        room_name=room_name, channel_consumer_class=TestYRoomChannelConsumer
    )
    async with fake_worker.start():
        # Connect to WS clients
        client_1 = WebsocketCommunicator(app, "/testws/")
        client_2 = WebsocketCommunicator(app_2, "/testws/")
        connected, _ = await client_1.connect()
        assert connected

        message = await fake_worker.wait_for_message()
        assert message["type"] == "connect"
        assert message["room"] == room_name
        assert message["conn_id"] == app.conn_id

        # which will forward it to websocket consumer
        payload = await client_1.receive_from()
        assert payload == SYNC_STEP_1

        connected, _ = await client_2.connect()
        assert connected

        # Client 2 should also receive a sync step1 message after connect
        message = await fake_worker.wait_for_message()
        assert message["type"] == "connect"
        assert message["room"] == room_name
        assert message["conn_id"] == app_2.conn_id

        payload = await client_2.receive_from()
        assert payload == SYNC_STEP_1

        await client_1.send_to(bytes_data=SYNC_STEP_1)
        message = await fake_worker.wait_for_message()
        assert message["type"] == "message"
        assert message["room"] == room_name
        assert message["conn_id"] == app.conn_id
        assert message["payload"] == SYNC_STEP_1

        payload = await client_1.receive_from()
        assert payload == SYNC_STEP_2

        assert await client_1.receive_nothing()
        assert await client_2.receive_nothing()

        # Send awareness update from client 1
        await client_1.send_to(bytes_data=AWARENESS_UPDATE)
        message = await fake_worker.wait_for_message()
        assert message["type"] == "message"
        assert message["room"] == room_name
        assert message["conn_id"] == app.conn_id
        assert message["payload"] == AWARENESS_UPDATE

        # Update is broadcast to all clients
        payload = await client_1.receive_from()
        assert payload == AWARENESS_UPDATE

        payload = await client_2.receive_from()
        assert payload == AWARENESS_UPDATE

        # check that no more messages are pending
        assert await client_1.receive_nothing()
        assert await client_2.receive_nothing()

        # Disconnect client 2
        await client_2.disconnect()

        message = await fake_worker.wait_for_message()
        assert message["type"] == "disconnect"
        assert message["room"] == room_name
        assert message["conn_id"] == app_2.conn_id

        # Client one gets awareness update
        payload = await client_1.receive_from()
        assert payload == AWARENESS_UPDATE

        assert await client_1.receive_nothing()

        # Disconnect client 1
        await client_1.disconnect()
        message = await fake_worker.wait_for_message()
        assert message["type"] == "disconnect"
        assert message["room"] == room_name
        assert message["conn_id"] == app.conn_id

        await fake_worker.shutdown()
        assert worker_results["shutdown"]


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_snapshot_yroom_consumer(settings):
    settings.YROOM_SETTINGS = {
        "default": {
            "STORAGE_BACKEND": "channels_yroom.storage.YDocDatabaseStorage",
            "REMOVE_ROOM_DELAY": 0,
        }
    }

    worker_results = {}

    class TestConsumer(YroomConsumer):
        pass

    class TestYRoomChannelConsumer(YRoomChannelConsumer):
        async def shutdown(self, message):
            worker_results["shutdown"] = True
            await super().shutdown(message)

    SYNC_STEP_1 = b"\x00\x00\x07\x01\xe9\xdb\x9a\x90\x01\x06"
    SYNC_STEP_2 = b"\x00\x01\x02\x00\x00"
    # state as update of a doc {"test": "hello"}
    DOC_DATA = b"\x01\x01\xe9\xdb\x9a\x90\x01\x00\x04\x01\x04test\x06hello \x00"

    app = TestConsumer()
    room_name = app.get_room_name()

    ydoc_update = await YDocUpdate.objects.acreate(
        name=room_name,
        data=DOC_DATA,
    )
    timestamp = ydoc_update.timestamp

    fake_worker = FakeWorker.from_defaults(
        room_name=room_name, channel_consumer_class=TestYRoomChannelConsumer
    )
    async with fake_worker.start():
        # Connect to WS clients
        client_1 = WebsocketCommunicator(app, "/testws/")
        connected, _ = await client_1.connect()
        assert connected

        message = await fake_worker.wait_for_message()
        assert message["type"] == "connect"
        assert message["room"] == room_name
        assert message["conn_id"] == app.conn_id

        # which will forward it to websocket consumer
        payload = await client_1.receive_from()
        assert payload == SYNC_STEP_1

        await client_1.send_to(bytes_data=SYNC_STEP_1)
        message = await fake_worker.wait_for_message()
        assert message["type"] == "message"
        assert message["room"] == room_name
        assert message["conn_id"] == app.conn_id
        assert message["payload"] == SYNC_STEP_1

        payload = await client_1.receive_from()
        assert payload == SYNC_STEP_2

        await client_1.disconnect()
        message = await fake_worker.wait_for_message()
        assert message["type"] == "disconnect"
        assert message["room"] == room_name
        assert message["conn_id"] == app.conn_id

        await fake_worker.shutdown()
        assert worker_results["shutdown"]

        ydoc_update = await YDocUpdate.objects.aget(name=room_name)
        assert ydoc_update.timestamp > timestamp
        assert ydoc_update.timestamp > timestamp
        assert ydoc_update.timestamp > timestamp


@pytest.mark.asyncio
async def test_export(settings, yroom_worker):
    settings.YROOM_SETTINGS = {
        "default": {
            "STORAGE_BACKEND": "channels_yroom.storage.YDocMemoryStorage",
            "REMOVE_ROOM_DELAY": 0,
        }
    }

    room_name = "yroom_default"
    channel_layer = get_channel_layer()

    d1 = Y.YDoc()
    text = d1.get_text("text")
    test_text = "hello world!"
    array = d1.get_array("array")
    test_array = [1, "foo", True]
    map = d1.get_map("map")
    test_map = {"a": 1}
    xml_element = d1.get_xml_element("xml_element")
    with d1.begin_transaction() as txn:
        text.extend(txn, test_text)
        array.extend(txn, test_array)
        map.update(txn, test_map)

        b = xml_element.push_xml_text(txn)
        a = xml_element.insert_xml_element(txn, 0, "p")
        aa = a.push_xml_text(txn)
        aa.push(txn, "hello")
        b.push(txn, "world")

    update_data = Y.encode_state_as_update(d1)
    storage = get_ydoc_storage(room_name)
    await storage.save_snapshot(room_name, update_data)

    proxy = YroomDocument(room_name, channel_layer)
    result = await proxy.export_text("text")
    assert result == test_text
    result = await proxy.export_array("array")
    assert result == test_array
    result = await proxy.export_map("map")
    assert result == test_map
    result = await proxy.export_xml_element("xml_element")
    assert result == "<UNDEFINED><p>hello</p>world</UNDEFINED>"

    # Non-existing elements return their defaults
    result = await proxy.export_text("no-text")
    assert result == ""
    result = await proxy.export_array("no-array")
    assert result == []
    result = await proxy.export_map("no-map")
    assert result == {}
    result = await proxy.export_xml_element("no-xml_element")
    # TODO: checkout this weirdness
    assert result == "<no-xml_element></no-xml_element>"


@pytest.mark.asyncio
async def test_export_bad_room(yroom_worker):
    proxy = YroomDocument("bad-room")
    with pytest.raises(DataUnavailable):
        await proxy.export_text("text")
    with pytest.raises(DataUnavailable):
        await proxy.export_array("array")
    with pytest.raises(DataUnavailable):
        await proxy.export_map("map")
    with pytest.raises(DataUnavailable):
        await proxy.export_xml_element("xml_element")
