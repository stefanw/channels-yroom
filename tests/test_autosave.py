import asyncio
import pytest

from channels_yroom.conf import get_default_room_settings
from channels_yroom.autosave import Autosave


class FakeChannelConsumer:
    def __init__(self):
        self.savedRooms = []

    async def snapshot_room(self, room_name: str):
        self.savedRooms.append(room_name)


def test_autosave_is_turned_off_by_default_and_nuding_has_no_effect():
    settings = get_default_room_settings()

    assert settings["AUTOSAVE_DELAY"] is None

    autosave = Autosave(consumer=None)
    autosave.nudge("not_present")

    assert not autosave.due_times
    assert not autosave.saver_tasks


@pytest.mark.django_db
def test_delay_needs_to_be_strictly_positive(settings):
    settings.YROOM_SETTINGS = {"invalid": {"AUTOSAVE_DELAY": -1.0}}
    autosave = Autosave(consumer=None)

    with pytest.raises(ValueError) as e:
        autosave.nudge("invalid")

    assert "Autosave delay time has to be strictly positive" in str(e.value)


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_nuding_multiple_times_postpones_saving(settings):
    settings.YROOM_SETTINGS = {
        "some_room": {"AUTOSAVE_DELAY": 0.1},
    }
    consumer = FakeChannelConsumer()
    autosave = Autosave(consumer)

    autosave.nudge("some_room")
    await asyncio.sleep(0.05)
    autosave.nudge("some_room")
    await asyncio.sleep(0.1)

    await asyncio.gather(*autosave.saver_tasks.values())

    assert consumer.savedRooms == ["some_room"]


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_faster_autosaving_overtakes_slower_one(settings):
    settings.YROOM_SETTINGS = {
        "slow": {"AUTOSAVE_DELAY": 0.1},
        "fast": {"AUTOSAVE_DELAY": 0.01},
    }
    consumer = FakeChannelConsumer()
    autosave = Autosave(consumer)

    autosave.nudge("slow")
    autosave.nudge("fast")
    await asyncio.sleep(0.1)

    await asyncio.gather(*autosave.saver_tasks.values())

    assert consumer.savedRooms == ["fast", "slow"]


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_forgetting_about_room_aborts_saving_and_is_graceful(settings):
    settings.YROOM_SETTINGS = {
        "some_room": {"AUTOSAVE_DELAY": 0.1},
    }
    consumer = FakeChannelConsumer()
    autosave = Autosave(consumer)

    autosave.nudge("some_room")
    await asyncio.sleep(0.05)
    autosave.forget("some_room")
    autosave.forget("some_room")  # Graceful?
    await asyncio.sleep(0.1)

    await asyncio.gather(*autosave.saver_tasks.values())

    assert consumer.savedRooms == []


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_canceling_everything(settings):
    settings.YROOM_SETTINGS = {
        "some_room": {"AUTOSAVE_DELAY": 0.1},
        "another_room": {"AUTOSAVE_DELAY": 0.1},
    }
    autosave = Autosave(consumer=None)

    autosave.nudge("some_room")
    autosave.nudge("another_room")
    tasks = list(autosave.saver_tasks.values())

    await autosave.cancel_all()

    for task in tasks:
        assert task.cancelled()

    assert not autosave.due_times
    assert not autosave.saver_tasks
