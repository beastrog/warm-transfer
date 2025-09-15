from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid

from models import (
    CreateRoomRequest,
    CreateRoomResponse,
    JoinTokenRequest,
    JoinTokenResponse,
    TransferRequest,
    TransferResponse,
    RoomSummaryResponse,
)
from services.livekit_client import mint_access_token
from services.llm_client import generate_summary
from services import transcripts

app = FastAPI(title="Warm Transfer MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/create-room", response_model=CreateRoomResponse)
def create_room(req: CreateRoomRequest):
    room_name = req.room_name or f"room-{uuid.uuid4().hex[:8]}"
    try:
        token = mint_access_token(room_name=room_name, identity=req.identity, role=req.role)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create room/token: {e}")
    return CreateRoomResponse(room_name=room_name, token=token)


@app.post("/join-token", response_model=JoinTokenResponse)
def join_token(req: JoinTokenRequest):
    try:
        token = mint_access_token(room_name=req.room_name, identity=req.identity, role="participant")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to mint token: {e}")
    return JoinTokenResponse(token=token)


@app.post("/transfer", response_model=TransferResponse)
def transfer(req: TransferRequest):
    to_room = req.to_room or f"room-{uuid.uuid4().hex[:8]}"

    if req.transcript and req.transcript.strip():
        transcripts.set_transcript(room_name=req.from_room, transcript_text=req.transcript.strip())

    existing_transcript = transcripts.get_transcript(req.from_room)
    summary_text = generate_summary(existing_transcript or "")

    transcripts.set_summary(room_name=to_room, summary_text=summary_text)
    if existing_transcript:
        transcripts.set_transcript(room_name=to_room, transcript_text=existing_transcript)

    try:
        initiator_token = mint_access_token(room_name=to_room, identity=req.initiator_identity, role="agent")
        target_token = mint_access_token(room_name=to_room, identity=req.target_identity, role="agent")
        caller_identity = os.getenv("CALLER_IDENTITY", "caller")
        caller_token = mint_access_token(room_name=to_room, identity=caller_identity, role="caller")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to mint transfer tokens: {e}")

    return TransferResponse(
        to_room=to_room,
        initiator_token=initiator_token,
        target_token=target_token,
        caller_token=caller_token,
        summary=summary_text,
    )


@app.get("/room/{room_name}/summary", response_model=RoomSummaryResponse)
def room_summary(room_name: str):
    return RoomSummaryResponse(
        summary=transcripts.get_summary(room_name) or "",
        transcript=transcripts.get_transcript(room_name) or "",
    )
