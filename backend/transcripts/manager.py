"""
Module for handling call transcripts and related operations.
"""
from typing import Dict, List, Optional, Any
import json
import logging
import time

logger = logging.getLogger(__name__)

# Global store for room data
ROOM_STORE: Dict[str, Dict[str, Any]] = {}

class TranscriptManager:
    """Manages call transcripts and related operations."""
    
    def __init__(self):
        self.transcripts: Dict[str, List[Dict]] = {}
        self.room_transcripts: Dict[str, List[str]] = {}
        self.room_summaries: Dict[str, str] = {}
    
    async def add_transcript_entry(
        self, 
        call_sid: str, 
        text: str, 
        speaker: str, 
        timestamp: Optional[float] = None
    ) -> None:
        """Add a new entry to the transcript.
        
        Args:
            call_sid: The unique identifier for the call
            text: The transcribed text
            speaker: The speaker identifier
            timestamp: Optional timestamp of the transcription
        """
        if call_sid not in self.transcripts:
            self.transcripts[call_sid] = []
            
        entry = {
            'text': text,
            'speaker': speaker,
            'timestamp': timestamp or time.time()
        }
        
        self.transcripts[call_sid].append(entry)
        logger.debug(f"Added transcript entry for call {call_sid}")
    
    async def get_transcript(self, call_sid: str) -> List[Dict]:
        """Retrieve the full transcript for a call.
        
        Args:
            call_sid: The unique identifier for the call
            
        Returns:
            List of transcript entries
        """
        return self.transcripts.get(call_sid, [])
    
    async def get_formatted_transcript(self, call_sid: str) -> str:
        """Get a formatted string of the transcript.
        
        Args:
            call_sid: The unique identifier for the call
            
        Returns:
            Formatted transcript as a string
        """
        transcript = await self.get_transcript(call_sid)
        if not transcript:
            return "No transcript available."
            
        formatted = []
        for entry in transcript:
            formatted.append(f"[{entry['speaker']}] {entry['text']}")
            
        return "\n".join(formatted)
    
    async def clear_transcript(self, call_sid: str) -> bool:
        """Clear the transcript for a call.
        
        Args:
            call_sid: The unique identifier for the call
            
        Returns:
            True if transcript was cleared, False if not found
        """
        if call_sid in self.transcripts:
            del self.transcripts[call_sid]
            return True
        return False

    def set_room_transcript(self, room_name: str, transcript: str) -> None:
        """Set a transcript for a room.
        
        Args:
            room_name: The unique identifier for the room
            transcript: The transcript text to store
        """
        if room_name not in self.room_transcripts:
            self.room_transcripts[room_name] = []
        self.room_transcripts[room_name].append(transcript)
        logger.debug(f"Added transcript for room {room_name}")

    def get_room_transcripts(self, room_name: str) -> List[str]:
        """Get all transcripts for a room.
        
        Args:
            room_name: The unique identifier for the room
            
        Returns:
            List of transcript entries
        """
        return self.room_transcripts.get(room_name, [])

    def set_room_summary(self, room_name: str, summary: str) -> None:
        """Set a summary for a room.
        
        Args:
            room_name: The unique identifier for the room
            summary: The summary text to store
        """
        self.room_summaries[room_name] = summary
        logger.debug(f"Added summary for room {room_name}")

    def get_room_summary(self, room_name: str) -> Optional[str]:
        """Get the summary for a room.
        
        Args:
            room_name: The unique identifier for the room
            
        Returns:
            Summary text if available, None otherwise
        """
        return self.room_summaries.get(room_name)

# Global instance
transcript_manager = TranscriptManager()

# For compatibility with direct module imports
def set_room_transcript(room_name: str, transcript: str) -> None:
    transcript_manager.set_room_transcript(room_name, transcript)

def get_room_transcripts(room_name: str) -> List[str]:
    return transcript_manager.get_room_transcripts(room_name)

def set_room_summary(room_name: str, summary: str) -> None:
    transcript_manager.set_room_summary(room_name, summary)

def get_room_summary(room_name: str) -> Optional[str]:
    return transcript_manager.get_room_summary(room_name)