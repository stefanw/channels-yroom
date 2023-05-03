from typing import Optional

from django.http import HttpResponse
from django.shortcuts import render

from channels_yroom.proxy import YroomDocument

from .consumers import get_room_name


def index(request):
    return render(request, "textcollab/index.html")


def room(request, room_name):
    return render(request, "textcollab/room.html", {"room_name": room_name})


YDOC_XML_FRAGMENT_KEY = "prosemirror"


async def save_room(request, room_name):
    # Get the XML fragment from the server ydoc
    room_group_name = get_room_name(room_name)
    doc = YroomDocument(room_group_name)
    result: Optional[str] = await doc.export_xml_fragment(YDOC_XML_FRAGMENT_KEY)
    if result is None:
        return HttpResponse(status=404)
    return HttpResponse(result)
