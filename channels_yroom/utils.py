from enum import Enum
from typing import Any, List, Optional, TypedDict


class YroomChannelResponse(TypedDict):
    type: str
    payload: bytes


class YroomChannelMessageType(str, Enum):
    connect = "connect"
    disconnect = "disconnect"
    message = "message"
    rpc = "rpc"


class _YroomChannelMessage(TypedDict):  # implicitly total=True
    type: YroomChannelMessageType
    room: str
    conn_id: int


class YroomChannelMessage(_YroomChannelMessage, total=False):
    payload: bytes


class YroomChannelRPCMessage(TypedDict):
    type: str
    room: str
    channel: str
    method: str
    params: List[Any]


class YroomChannelRPCResponse(TypedDict):
    type: str
    result: Optional[str]


def get_connection_group_name(conn_id) -> str:
    return "yroom-connection_%s" % conn_id
