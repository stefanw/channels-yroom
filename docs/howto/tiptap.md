# Use TipTap Hocuspocus provider

If you are using the TipTap Editor framework with the Collaboration extension via TipTap's `HocusPocusProvider`, you need to configure your room settings to adapt to the difference from the standard Yjs network protocol.

For example with a editor client like so:


```javascript
import { HocuspocusProvider } from '@hocuspocus/provider';
import Collaboration from '@tiptap/extension-collaboration';
import StarterKit from '@tiptap/starter-kit';
import { Editor } from '@tiptap/vue-3';

import * as Y from 'yjs';

const wsUrl = `ws${window.location.protocol === 'https:' ? 's' : ''}://${window.location.host}/ws/text-editor-collab/1`
const ydoc = new Y.Doc()
const documentName = 'text'

const provider = new HocuspocusProvider({
    url: wsUrl,
    name: documentName,
    document: ydoc,
})

new Editor({
    extensions: [
    StarterKit.configure({
        // The Collaboration extension comes with its own history handling
        history: false,
    }),
    Collaboration.configure({
        document: ydoc,
    }),
    ]
})
```

Your `consumers.py` could look like this:

```python
from channels_yroom.consumer import YroomConsumer


def get_room_name(room_name: str) -> str:
    # The room prefix is 'tiptap-editor'
    return "tiptap-editor.%s" % room_name


class TextEditorCollabConsumer(YroomConsumer):
    def get_room_name(self) -> str:
        room_name = str(self.scope["url_route"]["kwargs"]["pk"])
        return get_room_name(room_name)
```

Your `settings.py` should contain the following:

```python
YROOM_ROOM_SETTINGS = {
    "tiptap-editor": {
        # HocuspocusProvider adds and expects a name prefix
        "name_prefixed": True,
        # Since the server doesn't know the name on connect,
        # it has to wait for communication from client
        "server_sync_first": False,
    }
}
```

To complete this example, here is the `routing.py`

```python
from django.urls import re_path

from . import consumers

ws_urlpatterns = [
    re_path(
        r"ws/text-editor-collab/(?P<pk>\d+)$",
        consumers.TextEditorCollabConsumer.as_asgi(),
    ),
]
```

