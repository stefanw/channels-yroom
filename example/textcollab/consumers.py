from channels_yroom.consumer import YroomConsumer


class TextCollabConsumer(YroomConsumer):
    def get_room_group_name(self) -> str:
        room_name = self.scope["url_route"]["kwargs"]["room_name"]
        return "textcollab_%s" % room_name
