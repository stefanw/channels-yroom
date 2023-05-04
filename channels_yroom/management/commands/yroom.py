import logging

from channels import DEFAULT_CHANNEL_LAYER
from channels.layers import get_channel_layer
from django.core.management import BaseCommand, CommandError

from ...conf import get_default_room_settings
from ...worker import YroomWorker

logger = logging.getLogger("django.channels.worker")


class Command(BaseCommand):
    leave_locale_alone = True
    worker_class = YroomWorker

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            "--layer",
            action="store",
            dest="layer",
            default=DEFAULT_CHANNEL_LAYER,
            help="Channel layer alias to use, if not the default.",
        )
        parser.add_argument(
            "--channel",
            action="store",
            dest="channel",
            default=None,
            help="Channel layer alias to use, if not the default.",
        )

    def handle(self, *args, **options):
        # Get the backend to use
        self.verbosity = options.get("verbosity", 1)
        # Get the channel layer they asked for (or see if one isn't configured)
        if "layer" in options:
            self.channel_layer = get_channel_layer(options["layer"])
        else:
            self.channel_layer = get_channel_layer()
        if self.channel_layer is None:
            raise CommandError("You do not have any CHANNEL_LAYERS configured.")
        channel = None
        if "channel" in options:
            channel = options["channel"]
        if channel is None:
            channel = get_default_room_settings()["CHANNEL_NAME"]
        # Run the worker
        self.stdout.write("Running worker for channel '%s'\n" % channel)
        worker = self.worker_class(
            channel=channel,
            channel_layer=self.channel_layer,
        )
        worker.run()
