from channels_yroom.consumer import YroomConsumer


def get_room_name(room_name: str) -> str:
    return "textcollab_%s" % room_name


class TextCollabConsumer(YroomConsumer):
    def get_room_name(self) -> str:
        room_name = self.scope["url_route"]["kwargs"]["room_name"]
        return get_room_name(room_name)
