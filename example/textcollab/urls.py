from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path(
        "tiptap/<slug:room_name>/save/",
        views.save_room,
        name="save_room-tiptap",
        kwargs={"editor": "tiptap"},
    ),
    path(
        "tiptap/<slug:room_name>/", views.room, name="room", kwargs={"editor": "tiptap"}
    ),
    path(
        "prosemirror/<slug:room_name>/save/",
        views.save_room,
        name="save_room-prosemirror",
        kwargs={"editor": "prosemirror"},
    ),
    path(
        "prosemirror/<slug:room_name>/",
        views.room,
        name="room",
        kwargs={"editor": "prosemirror"},
    ),
]
