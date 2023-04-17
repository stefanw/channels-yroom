from enum import Enum
from typing import TypedDict


class YroomChannelResponse(TypedDict):
    type: str
    payload: bytes


class YroomChannelMessageType(str, Enum):
    connect = "connect"
    disconnect = "disconnect"
    message = "message"


class _YroomChannelMessage(TypedDict):  # implicitly total=True
    type: YroomChannelMessageType
    room: str
    conn_id: int


class YroomChannelMessage(_YroomChannelMessage, total=False):
    payload: bytes


def get_connection_group_name(conn_id) -> str:
    return "yroom-connection_%s" % conn_id
