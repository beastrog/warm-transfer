import logging
from typing import Dict, List, Optional

from backend.services.database import (
    ensure_room_exists,
    set_transcript,
    append_transcript,
    get_transcripts,
    set_summary,
    get_summary
)

logger = logging.getLogger(__name__)

# Legacy in-memory store - kept for backward compatibility during migration
# Will be removed in future versions
ROOM_STORE: Dict[str, Dict] = {}


def ensure_room(room_name: str) -> None:
    """Ensure a room exists in both legacy and new storage."""
    # Legacy in-memory store
    if room_name not in ROOM_STORE:
        ROOM_STORE[room_name] = {}
        ROOM_STORE[room_name]["transcripts"] = []
    
    # New database storage
    ensure_room_exists(room_name)


def set_room_transcript(room_name: str, transcript: str) -> None:
    """Set a transcript for a room."""
    ensure_room(room_name)
    
    # Legacy in-memory store
    ROOM_STORE[room_name]["transcripts"] = [transcript]
    
    # New database storage
    set_transcript(room_name, transcript)
    logger.info(f"Transcript set for room {room_name}")


def append_room_transcript(room_name: str, transcript: str) -> None:
    """Append to a room's transcript."""
    ensure_room(room_name)
    
    # Legacy in-memory store
    ROOM_STORE[room_name]["transcripts"].append(transcript)
    
    # New database storage
    append_transcript(room_name, transcript)
    logger.info(f"Transcript appended for room {room_name}")


def get_room_transcripts(room_name: str) -> List[str]:
    """Get all transcripts for a room."""
    ensure_room(room_name)
    
    # Try database first
    db_transcripts = get_transcripts(room_name)
    if db_transcripts:
        return db_transcripts
    
    # Fall back to legacy in-memory store
    return ROOM_STORE[room_name]["transcripts"]


def set_room_summary(room_name: str, summary: str) -> None:
    """Set a summary for a room."""
    ensure_room(room_name)
    
    # Legacy in-memory store
    ROOM_STORE[room_name]["summary"] = summary
    
    # New database storage
    set_summary(room_name, summary)
    logger.info(f"Summary set for room {room_name}")


def get_room_summary(room_name: str) -> Optional[str]:
    """Get the summary for a room."""
    ensure_room(room_name)
    
    # Try database first
    db_summary = get_summary(room_name)
    if db_summary is not None:
        return db_summary
    
    # Fall back to legacy in-memory store
    return ROOM_STORE[room_name].get("summary")
