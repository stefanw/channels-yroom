from enum import Enum
from typing import Any, List, Optional, TypedDict


class YroomChannelResponse(TypedDict):
    type: str
    payloads: List[bytes]


class YroomChannelMessageType(str, Enum):
    connect = "connect"
    disconnect = "disconnect"
    message = "message"
    rpc = "rpc"


class _YroomChannelMessage(TypedDict):  # implicitly total=True
    type: YroomChannelMessageType
    room: str
    conn_id: int
    channel_name: str


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
