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
