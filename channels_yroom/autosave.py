import asyncio
import time
from asyncio import Task
from typing import Dict, Callable

from .conf import get_room_settings
from .utils import YroomChannelMessage


class Autosave:

    """Automatically save room after some time of non-editing.

    The `nudge()` method can be used to signal editing activity and will
    schedule a save after `AUTOSAVE_DELAY` many seconds. Subsequent `nudge()`
    calls will postpone saving. Internally one saver task per room.

    Attributes:
        consumer: Channel consumer for snapshotting room.
        time_func: Callable returning a monotonic timestamp.
        due_times: Next update per room.
        saver_tasks: Saver tasks per room.
    """

    def __init__(self, consumer: "YRoomChannelConsumer"):
        """Args:
            consumer: YroomConsumer instance used for snapshot_room() saving.
        """
        self.consumer = consumer
        self.time_func: Callable[[], float] = time.perf_counter
        self.due_times: Dict[str, float] = {}
        self.saver_tasks: Dict[str, Task] = {}

    def nudge(self, room_name: str) -> None:
        """Signal editing activity for a room. Schedule autosave in
        AUTOSAVE_DELAY many seconds. Postpone existing autosavings. Has no
        effect if AUTOSAVE_DELAY is not defined for this room.
        """
        room_settings = get_room_settings(room_name)
        delay = room_settings["AUTOSAVE_DELAY"]
        if delay is None:
            return

        if delay <= 0:
            raise ValueError("Autosave delay time has to be strictly positive")

        now = self.time_func()
        self.due_times[room_name] = now + delay
        if room_name in self.saver_tasks:
            return

        task = asyncio.create_task(self.snapshot_room_soon(room_name))
        task.add_done_callback(lambda _task: self.forget(room_name))
        self.saver_tasks[room_name] = task

    async def snapshot_room_soon(self, room_name: str):
        """Snapshot room in due time."""
        while True:
            now = self.time_func()
            when = self.due_times[room_name]
            if now < when:
                await asyncio.sleep(when - now)
            else:
                break

        await self.consumer.snapshot_room(room_name)

    def forget(self, room_name: str) -> None:
        """Forget about a room."""
        if room_name in self.saver_tasks:
            task = self.saver_tasks.pop(room_name)
            task.cancel()

        self.due_times.pop(room_name, None)

    async def cancel_all(self) -> None:
        """Cancel all auto saving."""
        tasks = self.saver_tasks.values()
        for task in tasks:
            task.cancel()

        await asyncio.gather(*tasks, return_exceptions=True)
        self.saver_tasks.clear()
        self.due_times.clear()
