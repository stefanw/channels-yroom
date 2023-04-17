from django.conf import settings  # noqa
from appconf import AppConf


class YroomAppConf(AppConf):
    CHANNEL_NAME = "yroom"
    REMOVE_ROOM_DELAY = 30  # in seconds
    STORAGE_BACKEND = "channels_yroom.storage.YDocDatabaseStorage"

    class Meta:
        prefix = "yroom"
