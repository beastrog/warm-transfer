"""
Transcripts package for handling call transcripts and related operations.
"""

from .manager import (
    TranscriptManager,
    transcript_manager,
    get_room_transcripts,
    set_room_transcript,
    get_room_summary,
    set_room_summary
)

__all__ = [
    'TranscriptManager',
    'transcript_manager',
    'get_room_transcripts',
    'set_room_transcript',
    'get_room_summary',
    'set_room_summary'
]
