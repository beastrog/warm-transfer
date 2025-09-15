import pytest
import os
import sys
import sqlite3
from unittest.mock import patch, MagicMock

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.database import (
    initialize_database,
    ensure_room_exists,
    set_transcript,
    append_transcript,
    get_transcripts,
    set_summary,
    get_summary,
    set_call_status,
    get_call_status,
    DB_PATH
)


@pytest.fixture
def test_db():
    # Use in-memory database for testing
    test_db_path = ":memory:"
    with patch('services.database.DB_PATH', test_db_path):
        # Initialize the database
        conn = sqlite3.connect(test_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            room_name TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS transcripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_name TEXT,
            transcript TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (room_name) REFERENCES rooms (room_name)
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS summaries (
            room_name TEXT PRIMARY KEY,
            summary TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (room_name) REFERENCES rooms (room_name)
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS call_status (
            room_name TEXT PRIMARY KEY,
            twilio_call_sid TEXT,
            status TEXT,
            phone_number TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (room_name) REFERENCES rooms (room_name)
        )
        """)
        
        conn.commit()
        yield
        conn.close()


def test_ensure_room_exists(test_db):
    """Test that ensure_room_exists creates a room if it doesn't exist."""
    room_name = "test-room"
    ensure_room_exists(room_name)
    
    # Verify the room was created
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rooms WHERE room_name = ?", (room_name,))
    result = cursor.fetchone()
    conn.close()
    
    assert result is not None
    assert result["room_name"] == room_name


def test_set_transcript(test_db):
    """Test that set_transcript adds a transcript to a room."""
    room_name = "test-room"
    transcript = "This is a test transcript."
    set_transcript(room_name, transcript)
    
    # Verify the transcript was added
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transcripts WHERE room_name = ?", (room_name,))
    result = cursor.fetchone()
    conn.close()
    
    assert result is not None
    assert result["room_name"] == room_name
    assert result["transcript"] == transcript


def test_append_transcript(test_db):
    """Test that append_transcript adds a transcript to a room."""
    room_name = "test-room"
    transcript1 = "This is the first transcript."
    transcript2 = "This is the second transcript."
    
    append_transcript(room_name, transcript1)
    append_transcript(room_name, transcript2)
    
    # Verify both transcripts were added
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transcripts WHERE room_name = ? ORDER BY timestamp", (room_name,))
    results = cursor.fetchall()
    conn.close()
    
    assert len(results) == 2
    assert results[0]["transcript"] == transcript1
    assert results[1]["transcript"] == transcript2


def test_get_transcripts(test_db):
    """Test that get_transcripts returns all transcripts for a room."""
    room_name = "test-room"
    transcript1 = "This is the first transcript."
    transcript2 = "This is the second transcript."
    
    append_transcript(room_name, transcript1)
    append_transcript(room_name, transcript2)
    
    # Get the transcripts
    transcripts = get_transcripts(room_name)
    
    assert len(transcripts) == 2
    assert transcripts[0] == transcript1
    assert transcripts[1] == transcript2


def test_set_summary(test_db):
    """Test that set_summary adds a summary to a room."""
    room_name = "test-room"
    summary = "This is a test summary."
    set_summary(room_name, summary)
    
    # Verify the summary was added
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM summaries WHERE room_name = ?", (room_name,))
    result = cursor.fetchone()
    conn.close()
    
    assert result is not None
    assert result["room_name"] == room_name
    assert result["summary"] == summary


def test_get_summary(test_db):
    """Test that get_summary returns the summary for a room."""
    room_name = "test-room"
    summary = "This is a test summary."
    set_summary(room_name, summary)
    
    # Get the summary
    result = get_summary(room_name)
    
    assert result == summary


def test_set_call_status(test_db):
    """Test that set_call_status adds call status to a room."""
    room_name = "test-room"
    twilio_call_sid = "CA123456789"
    status = "in-progress"
    phone_number = "+12345678901"
    
    set_call_status(room_name, twilio_call_sid, status, phone_number)
    
    # Verify the call status was added
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM call_status WHERE room_name = ?", (room_name,))
    result = cursor.fetchone()
    conn.close()
    
    assert result is not None
    assert result["room_name"] == room_name
    assert result["twilio_call_sid"] == twilio_call_sid
    assert result["status"] == status
    assert result["phone_number"] == phone_number


def test_get_call_status(test_db):
    """Test that get_call_status returns the call status for a room."""
    room_name = "test-room"
    twilio_call_sid = "CA123456789"
    status = "in-progress"
    phone_number = "+12345678901"
    
    set_call_status(room_name, twilio_call_sid, status, phone_number)
    
    # Get the call status
    result = get_call_status(room_name)
    
    assert result is not None
    assert result["twilio_call_sid"] == twilio_call_sid
    assert result["status"] == status
    assert result["phone_number"] == phone_number