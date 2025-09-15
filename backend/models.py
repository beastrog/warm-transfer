from pydantic import BaseModel
from typing import Optional


class CreateRoomRequest(BaseModel):
    room_name: Optional[str] = None
    identity: str
    role: str


class CreateRoomResponse(BaseModel):
    room_name: str
    token: str


class JoinTokenRequest(BaseModel):
    room_name: str
    identity: str


class JoinTokenResponse(BaseModel):
    token: str


class TransferRequest(BaseModel):
    from_room: str
    initiator_identity: str
    target_identity: str
    to_room: Optional[str] = None
    transcript: Optional[str] = None


class TransferResponse(BaseModel):
    to_room: str
    initiator_token: str
    target_token: str
    caller_token: str
    summary: str


class RoomSummaryResponse(BaseModel):
    summary: str
    transcript: str
