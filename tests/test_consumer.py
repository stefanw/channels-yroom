import pytest
from asgiref.testing import ApplicationCommunicator
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator

from channels_yroom.channel import YRoomChannelConsumer
from channels_yroom.conf import get_room_settings
from channels_yroom.consumer import YroomConsumer
from channels_yroom.models import YDocUpdate


async def forward_to_yroom_worker(channel_layer, channel, worker_communicator):
    # Receive message on yroom channel layer...
    message = await channel_layer.receive(channel)
    # ... and give it to worker consumer
    await worker_communicator.send_input(message)
    return message


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
    worker = TestYRoomChannelConsumer()
    room_name = app.get_room_group_name()
    room_settings = get_room_settings(room_name)
    channel_layer = get_channel_layer()
    channel = room_settings["CHANNEL_NAME"]

    # Create a worker instance
    worker_communicator = ApplicationCommunicator(
        worker, {"type": "channel", "channel": channel}
    )

    # Connect to WS clients
    client_1 = WebsocketCommunicator(app, "/testws/")
    client_2 = WebsocketCommunicator(app_2, "/testws/")
    connected, _ = await client_1.connect()
    assert connected

    message = await forward_to_yroom_worker(channel_layer, channel, worker_communicator)
    assert message["type"] == "connect"
    assert message["room"] == room_name
    assert message["conn_id"] == app.conn_id

    # which will forward it to websocket consumer
    payload = await client_1.receive_from()
    assert payload == SYNC_STEP_1

    connected, _ = await client_2.connect()
    assert connected

    # Client 2 should also receive a sync step1 message after connect
    message = await forward_to_yroom_worker(channel_layer, channel, worker_communicator)
    assert message["type"] == "connect"
    assert message["room"] == room_name
    assert message["conn_id"] == app_2.conn_id

    payload = await client_2.receive_from()
    assert payload == SYNC_STEP_1

    await client_1.send_to(bytes_data=SYNC_STEP_1)
    message = await forward_to_yroom_worker(channel_layer, channel, worker_communicator)
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
    message = await forward_to_yroom_worker(channel_layer, channel, worker_communicator)
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
    message = await forward_to_yroom_worker(channel_layer, channel, worker_communicator)
    assert message["type"] == "disconnect"
    assert message["room"] == room_name
    assert message["conn_id"] == app_2.conn_id

    # Client one gets awareness update
    payload = await client_1.receive_from()
    assert payload == AWARENESS_UPDATE

    assert await client_1.receive_nothing()

    # Disconnect client 1
    await client_1.disconnect()
    message = await forward_to_yroom_worker(channel_layer, channel, worker_communicator)
    assert message["type"] == "disconnect"
    assert message["room"] == room_name
    assert message["conn_id"] == app.conn_id

    # Gracefully shutdown worker
    await worker_communicator.send_input({"type": "shutdown", "signal": "SIGTERM"})
    shutdown_confirmation = await worker_communicator.receive_output(1)
    assert shutdown_confirmation["type"] == "shutdown.complete"
    assert worker_results["shutdown"]
    await worker_communicator.wait()


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
    worker = TestYRoomChannelConsumer()
    room_name = app.get_room_group_name()
    room_settings = get_room_settings(room_name)
    channel_layer = get_channel_layer()
    channel = room_settings["CHANNEL_NAME"]
    ydoc_update = await YDocUpdate.objects.acreate(
        name=room_name,
        data=DOC_DATA,
    )
    timestamp = ydoc_update.timestamp

    # Create a worker instance
    worker_communicator = ApplicationCommunicator(
        worker, {"type": "channel", "channel": channel}
    )

    # Connect to WS clients
    client_1 = WebsocketCommunicator(app, "/testws/")
    connected, _ = await client_1.connect()
    assert connected

    message = await forward_to_yroom_worker(channel_layer, channel, worker_communicator)
    assert message["type"] == "connect"
    assert message["room"] == room_name
    assert message["conn_id"] == app.conn_id

    # which will forward it to websocket consumer
    payload = await client_1.receive_from()
    assert payload == SYNC_STEP_1

    await client_1.send_to(bytes_data=SYNC_STEP_1)
    message = await forward_to_yroom_worker(channel_layer, channel, worker_communicator)
    assert message["type"] == "message"
    assert message["room"] == room_name
    assert message["conn_id"] == app.conn_id
    assert message["payload"] == SYNC_STEP_1

    payload = await client_1.receive_from()
    assert payload == SYNC_STEP_2

    await client_1.disconnect()
    message = await forward_to_yroom_worker(channel_layer, channel, worker_communicator)
    assert message["type"] == "disconnect"
    assert message["room"] == room_name
    assert message["conn_id"] == app.conn_id

    await worker_communicator.send_input({"type": "shutdown", "signal": "SIGTERM"})
    shutdown_confirmation = await worker_communicator.receive_output(1)
    assert shutdown_confirmation["type"] == "shutdown.complete"
    assert worker_results["shutdown"]
    await worker_communicator.wait()

    ydoc_update = await YDocUpdate.objects.aget(name=room_name)
    assert ydoc_update.timestamp > timestamp
    assert ydoc_update.timestamp > timestamp
    assert ydoc_update.timestamp > timestamp
