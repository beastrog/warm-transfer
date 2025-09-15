from typing import Dict, Optional

# Simple in-memory room store
ROOM_STORE: Dict[str, Dict[str, str]] = {}


def _ensure_room(room_name: str) -> Dict[str, str]:
    if room_name not in ROOM_STORE:
        ROOM_STORE[room_name] = {"transcript": "", "summary": ""}
    return ROOM_STORE[room_name]


def set_transcript(*, room_name: str, transcript_text: str) -> None:
    room = _ensure_room(room_name)
    room["transcript"] = transcript_text


def append_transcript(*, room_name: str, transcript_text: str) -> None:
    room = _ensure_room(room_name)
    prev = room.get("transcript", "")
    room["transcript"] = (prev + "\n" + transcript_text).strip() if prev else transcript_text


def get_transcript(room_name: str) -> Optional[str]:
    room = ROOM_STORE.get(room_name)
    return room.get("transcript") if room else None


def set_summary(*, room_name: str, summary_text: str) -> None:
    room = _ensure_room(room_name)
    room["summary"] = summary_text


def get_summary(room_name: str) -> Optional[str]:
    room = ROOM_STORE.get(room_name)
    return room.get("summary") if room else None
