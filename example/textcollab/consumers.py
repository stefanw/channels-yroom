from urllib.parse import parse_qs

from yroom import YRoomClientOptions

from channels_yroom.consumer import YroomConsumer


def get_prosemirror_room_name(room_name: str) -> str:
    return "textcollab.%s" % room_name


def get_client_options(scope):
    params = parse_qs(scope["query_string"])
    read_only = params["readonly"]
    return YRoomClientOptions(
        allow_write=not read_only,
        allow_write_awareness=not read_only,
    )


class TextCollabConsumer(YroomConsumer):
    def get_room_name(self) -> str:
        room_name = self.scope["url_route"]["kwargs"]["room_name"]
        return get_prosemirror_room_name(room_name)

    async def get_client_options(self) -> YRoomClientOptions:
        return get_client_options(self.scope)


def get_tiptap_room_name(room_name: str) -> str:
    return "textcollab_tiptap.%s" % room_name


class TipTapConsumer(YroomConsumer):
    def get_room_name(self) -> str:
        room_name = self.scope["url_route"]["kwargs"]["room_name"]
        return get_tiptap_room_name(room_name)

    async def get_client_options(self) -> YRoomClientOptions:
        return get_client_options(self.scope)
