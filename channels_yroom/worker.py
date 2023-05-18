import asyncio
import logging
import signal

from .channel import YRoomChannelConsumer

logger = logging.getLogger(__name__)


class YroomWorker:
    SIGNALS = (
        signal.SIGHUP,
        signal.SIGTERM,
        signal.SIGINT,
    )
    consumer_class = YRoomChannelConsumer

    def __init__(self, channel, channel_layer):
        self.channel = channel
        self.channel_layer = channel_layer
        self.shutting_down = False

    def run(self):
        """
        Runs the asyncio event loop with our handler loop.
        """
        loop = asyncio.get_event_loop()
        self._setup_signal_handlers(loop)
        loop.set_exception_handler(self.handle_exception)
        try:
            loop.create_task(self.run_worker())
            loop.run_forever()
        finally:
            loop.close()

    def _setup_signal_handlers(self, loop):
        for sig in self.SIGNALS:
            loop.add_signal_handler(
                sig,
                lambda sig=sig: asyncio.create_task(self.shutdown_worker(loop, sig)),
            )

    def _clear_signal_handlers(self, loop):
        for sig in self.SIGNALS:
            loop.remove_signal_handler(sig)

    async def run_worker(self):
        """
        Runs the worker loop.
        This sidesteps the channels ASGI routing
        and runs the consumer directly to have better error handling.
        """
        self.input_queue = asyncio.Queue()
        asyncio.create_task(self.run_consumer())

        while True:
            if self.shutting_down:
                # Stop relaying messages when shutting down
                break
            message = await self.channel_layer.receive(self.channel)
            if not message.get("type", None):
                raise ValueError("Worker received message with no type.")
            # Add message to queue
            await self.input_queue.put(message)

    async def run_consumer(self):
        """
        Runs the consumer loop.
        """
        self.consumer = self.consumer_class()
        self.consumer.channel_layer = self.channel_layer
        self.consumer.base_send = self.receive_from_worker

        while True:
            if self.shutting_down:
                # Stop
                break
            message = await self.input_queue.get()
            # Dispatch directly to the consumer
            await self.consumer.dispatch(message)

    def handle_exception(self, loop, context):
        msg = context.get("exception", context["message"])
        if "exception" in context:
            import traceback

            traceback.print_tb(context["exception"].__traceback__)

        if self.shutting_down:
            logger.error(f"Caught exception while shutting down: {msg}")
            logger.info("Cancelling all tasks and stopping loop...")
            asyncio.create_task(self.complete_shutdown(loop))
            return

        logger.error(f"Caught exception: {msg}")
        logger.info("Shutting down...")
        asyncio.create_task(self.shutdown_worker(loop))

    async def shutdown_worker(self, loop, signal=None):
        """
        Shuts down worker gracefully.
        """
        if self.shutting_down:
            return
        self.shutting_down = True
        self._clear_signal_handlers(loop)
        if signal:
            logger.info(f"Received signal {signal.name}...")
            shutdown_message = {"type": "shutdown", "signal": signal.name}
        else:
            shutdown_message = {"type": "shutdown", "signal": None}

        self.shutdown_event = asyncio.Event()
        logger.info("Sending shutdown message to worker...")
        # Skip queue, send directly to consumer
        await self.consumer.dispatch(shutdown_message)
        logger.info("Waiting on cleanup...")
        await self.shutdown_event.wait()
        await self.complete_shutdown(loop)

    async def complete_shutdown(self, loop):
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        [task.cancel() for task in tasks]
        logger.info(f"Cancelling {len(tasks)} outstanding tasks")
        await asyncio.gather(*tasks, return_exceptions=True)
        loop.stop()
        logger.info("Shutdown worker complete")

    async def receive_from_worker(self, message):
        assert message["type"] == "shutdown.complete"
        self.shutdown_event.set()
