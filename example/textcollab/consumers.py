from channels_yroom.consumer import YroomConsumer


def get_prosemirror_room_name(room_name: str) -> str:
    return "textcollab.%s" % room_name


class TextCollabConsumer(YroomConsumer):
    def get_room_name(self) -> str:
        room_name = self.scope["url_route"]["kwargs"]["room_name"]
        return get_prosemirror_room_name(room_name)


def get_tiptap_room_name(room_name: str) -> str:
    return "textcollab_tiptap.%s" % room_name


class TipTapConsumer(YroomConsumer):
    def get_room_name(self) -> str:
        room_name = self.scope["url_route"]["kwargs"]["room_name"]
        return get_tiptap_room_name(room_name)
