import pytest
from django.conf import settings


def pytest_configure():
    settings.configure(
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3"}},
        INSTALLED_APPS=[
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.sessions",
            "django.contrib.admin",
            "channels",
            "channels_yroom",
        ],
        SECRET_KEY="Not_a_secret_key",
        CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}},
        YROOM_SETTINGS={
            "default": {
                "STORAGE_BACKEND": "channels_yroom.storage.YDocDummyStorage",
                "REMOVE_ROOM_DELAY": 0,
            }
        },
    )


class YData:
    SYNC_STEP_1 = b"\x00\x00\x01\x00"
    DOC_DATA = b"\x01\x01\xe9\xdb\x9a\x90\x01\x00\x04\x01\x04test\x06hello \x00"
    # Sync step one with doc data
    SYNC_STEP_1_DATA = b"\x00\x00\x07\x01\xe9\xdb\x9a\x90\x01\x06"
    SYNC_STEP_2 = b"\x00\x01\x02\x00\x00"
    AWARENESS_UPDATE = b"\x01\x01\x00"
    # state as update of a doc {"test": "hello"}


@pytest.fixture
def ydata():
    return YData
