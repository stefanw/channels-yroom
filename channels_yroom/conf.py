from django.conf import settings

DEFAULT_ROOM = "default"
PREFIX_SEPARATOR = "."
DEFAULTS = {
    "CHANNEL_NAME": "yroom",
    "REMOVE_ROOM_DELAY": 30,  # in seconds
    "STORAGE_BACKEND": "channels_yroom.storage.YDocDatabaseStorage",
    "PROTOCOL_VERSION": 1,
    "PROTOCOL_NAME_PREFIX": False,
    "SERVER_START_SYNC": True,
    "AUTOSAVE_DELAY": None,  # None for disabled or in strictly positive seconds
}


def get_settings():
    return getattr(settings, "YROOM_SETTINGS", {DEFAULT_ROOM: DEFAULTS.copy()})


def get_default_room_settings():
    return get_room_settings(DEFAULT_ROOM)


def get_room_settings(room_name):
    room_settings = DEFAULTS.copy()
    room_settings.update(find_room_settings(room_name))
    return room_settings


def get_room_prefix(room_name):
    return room_name.split(PREFIX_SEPARATOR, 1)[0]


def find_room_settings(room_name):
    prefix = get_room_prefix(room_name)
    yroom_settings = get_settings()
    if prefix in yroom_settings:
        return yroom_settings[prefix]
    try:
        return yroom_settings[DEFAULT_ROOM]
    except KeyError:
        return DEFAULTS.copy()
