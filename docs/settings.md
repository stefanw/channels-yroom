# Settings

`YROOM_SETTINGS` is a dictionary that maps room prefixes to room settings. Room settings under the `"default"` key are used if a room prefix doesn't match any other entry in `YROOM_SETTINGS`.

Room names can have a prefix that is separated by a dot character (`"."`), e.g. `"textcollab.42"` or `"textcollab.docs.23"` both search for the setting prefix `"textcollab"`.

This allows different settings for different room types distinguished via their prefix:

```python
# In your Django settings.py

YROOM_SETTINGS = {
    # Change default room removal delay to 60 seconds
    "default": {
        "REMOVE_ROOM_DELAY": 60,  # in seconds
        # Other values are taken from defaults
    },
    # Rooms with the "textcollab" prefix should stay around even longer
    # Applies to room names like "textcollab.1"
    "textcollab": {
        "REMOVE_ROOM_DELAY": 120,  # in seconds
    }
}
```

## List of settings

The following settings keys are available:

### `"CHANNEL_NAME"`
Default: `"yroom"`. The channel name on which to communicate with the worker process. This allows multiple workers listening on different channels per room prefix. This value needs to be provided to the yroom worker via `--channel` if not using the default.

### `"REMOVE_ROOM_DELAY"`
Default: `30` (in seconds). When the last client disconnects the worker will keep the room in memory for this amount of time before forgetting it (saving a snapshot first). When a client connects before the time is up, the eviction is canceled.

### `"STORAGE_BACKEND"`
Default: `"channels_yroom.storage.YDocDatabaseStorage"`. Storage backend to use.


### `"PROTOCOL_VERSION"`
Default: `1`. Yjs protocol encoder/decoder version to use. Currently untested but also possible value is `2`.

### `"PROTOCOL_NAME_PREFIX"`
Default: `False`. Whether to read and add a string prefix to the network protocol – as done by a client-side implementation.

### `"SERVER_START_SYNC"`
Default: `True`. Whether the server sends a sync request and awareness update on connect.
