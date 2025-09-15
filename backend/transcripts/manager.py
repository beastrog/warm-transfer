"""
Module for handling call transcripts and related operations.
"""
from typing import Dict, List, Optional
import json
import logging

logger = logging.getLogger(__name__)

class TranscriptManager:
    """Manages call transcripts and related operations."""
    
    def __init__(self):
        self.transcripts: Dict[str, List[Dict]] = {}
    
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

# Global instance
transcript_manager = TranscriptManager()
