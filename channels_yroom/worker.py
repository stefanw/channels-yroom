import asyncio
import logging
import signal

logger = logging.getLogger(__name__)


class YroomWorker:
    SIGNALS = (
        signal.SIGHUP,
        signal.SIGTERM,
        signal.SIGINT,
    )

    def __init__(self, application, channel, channel_layer):
        self.application = application
        self.channel = channel
        self.channel_layer = channel_layer

    def run(self):
        """
        Runs the asyncio event loop with our handler loop.
        """
        loop = asyncio.get_event_loop()
        self._setup_signal_handlers(loop)
        try:
            loop.create_task(self.run_worker())
            loop.run_forever()
        finally:
            loop.close()
            logger.info("Shutdown worker complete")

    def _setup_signal_handlers(self, loop):
        for sig in self.SIGNALS:
            loop.add_signal_handler(
                sig,
                lambda sig=sig: asyncio.create_task(self.shutdown_worker(sig, loop)),
            )

    def _clear_signal_handlers(self, loop):
        for sig in self.SIGNALS:
            loop.remove_signal_handler(sig)

    async def run_worker(self):
        scope = {"type": "channel", "channel": self.channel}
        self.input_queue = asyncio.Queue()
        self.task = asyncio.create_task(
            self.application(
                scope=scope,
                receive=self.input_queue.get,
                send=self.receive_from_worker,
            ),
        )
        # The consumer is also listening on a channel layer
        # but only on a new random channel
        # so we listen on the given channel and forward messages
        while True:
            message = await self.channel_layer.receive(self.channel)
            if not message.get("type", None):
                raise ValueError("Worker received message with no type.")
            # Run the message into the app
            await self.input_queue.put(message)

    async def shutdown_worker(self, signal, loop):
        """
        Shuts down worker gracefully.
        """
        self._clear_signal_handlers(loop)
        logger.info(f"Received signal {signal.name}...")
        shutdown_message = {"type": "shutdown", "signal": signal.name}
        self.shutdown_event = asyncio.Event()
        logger.info("Sending shutdown message to worker...")
        await self.input_queue.put(shutdown_message)
        logger.info("Waiting on cleanup...")
        await self.shutdown_event.wait()

        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        [task.cancel() for task in tasks]
        logger.info(f"Cancelling {len(tasks)} outstanding tasks")
        await asyncio.gather(*tasks, return_exceptions=True)

        loop.stop()

    async def receive_from_worker(self, message):
        assert message["type"] == "shutdown.complete"
        self.shutdown_event.set()
