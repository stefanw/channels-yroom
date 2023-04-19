from django.shortcuts import render


def index(request):
    return render(request, "textcollab/index.html")


def room(request, room_name):
    return render(request, "textcollab/room.html", {"room_name": room_name})
