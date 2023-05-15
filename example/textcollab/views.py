from typing import Optional

from django.http import HttpResponse
from django.shortcuts import render

from channels_yroom.proxy import DataUnavailable, YroomDocument

from .consumers import get_prosemirror_room_name, get_tiptap_room_name


def index(request):
    return render(request, "textcollab/index.html")


def room(request, room_name, editor="prosemirror"):
    return render(
        request,
        "textcollab/room.html",
        {
            "room_settings": {
                "roomName": room_name,
                "editor": editor,
                "wsPath": f"/ws/{editor}/",
            }
        },
    )


async def save_room(request, room_name, editor="prosemirror"):
    # Get the XML fragment from the server ydoc
    if editor == "prosemirror":
        room_group_name = get_prosemirror_room_name(room_name)
        YDOC_XML_FRAGMENT_KEY = "prosemirror"
    elif editor == "tiptap":
        room_group_name = get_tiptap_room_name(room_name)
        YDOC_XML_FRAGMENT_KEY = "default"
    doc = YroomDocument(room_group_name)
    try:
        result: Optional[str] = await doc.export_xml_fragment(YDOC_XML_FRAGMENT_KEY)
    except DataUnavailable:
        return HttpResponse(status=404)
    return HttpResponse(result)
