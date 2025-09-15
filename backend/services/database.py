import os
import json
import sqlite3
import logging
from typing import Dict, Any, List, Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Database configuration
DB_PATH = os.getenv("DB_PATH", "room_store.db")


@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        yield conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise
    finally:
        if conn:
            conn.close()


def initialize_database():
    """Initialize the database with required tables."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Create rooms table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS rooms (
                room_name TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # Create transcripts table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS transcripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_name TEXT,
                transcript TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (room_name) REFERENCES rooms (room_name)
            )
            """)
            
            # Create summaries table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS summaries (
                room_name TEXT PRIMARY KEY,
                summary TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (room_name) REFERENCES rooms (room_name)
            )
            """)
            
            # Create call_status table for Twilio integration
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
            logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def ensure_room_exists(room_name: str) -> None:
    """Ensure a room exists in the database."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO rooms (room_name) VALUES (?)",
                (room_name,)
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to ensure room exists: {e}")
        raise


def set_transcript(room_name: str, transcript: str) -> None:
    """Set a transcript for a room."""
    ensure_room_exists(room_name)
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO transcripts (room_name, transcript) VALUES (?, ?)",
                (room_name, transcript)
            )
            cursor.execute(
                "UPDATE rooms SET updated_at = CURRENT_TIMESTAMP WHERE room_name = ?",
                (room_name,)
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to set transcript: {e}")
        raise


def append_transcript(room_name: str, transcript: str) -> None:
    """Append to a room's transcript."""
    ensure_room_exists(room_name)
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO transcripts (room_name, transcript) VALUES (?, ?)",
                (room_name, transcript)
            )
            cursor.execute(
                "UPDATE rooms SET updated_at = CURRENT_TIMESTAMP WHERE room_name = ?",
                (room_name,)
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to append transcript: {e}")
        raise


def get_transcripts(room_name: str) -> List[str]:
    """Get all transcripts for a room."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT transcript FROM transcripts WHERE room_name = ? ORDER BY timestamp",
                (room_name,)
            )
            results = cursor.fetchall()
            return [row[0] for row in results]
    except Exception as e:
        logger.error(f"Failed to get transcripts: {e}")
        return []


def set_summary(room_name: str, summary: str) -> None:
    """Set a summary for a room."""
    ensure_room_exists(room_name)
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO summaries (room_name, summary, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                (room_name, summary)
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to set summary: {e}")
        raise


def get_summary(room_name: str) -> Optional[str]:
    """Get the summary for a room."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT summary FROM summaries WHERE room_name = ?",
                (room_name,)
            )
            result = cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        logger.error(f"Failed to get summary: {e}")
        return None


def set_call_status(room_name: str, twilio_call_sid: str, status: str, phone_number: str) -> None:
    """Set Twilio call status for a room."""
    ensure_room_exists(room_name)
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT OR REPLACE INTO call_status 
                   (room_name, twilio_call_sid, status, phone_number, updated_at) 
                   VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                (room_name, twilio_call_sid, status, phone_number)
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to set call status: {e}")
        raise


def get_call_status(room_name: str) -> Optional[Dict[str, Any]]:
    """Get Twilio call status for a room."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT twilio_call_sid, status, phone_number FROM call_status WHERE room_name = ?",
                (room_name,)
            )
            result = cursor.fetchone()
            if result:
                return {
                    "twilio_call_sid": result[0],
                    "status": result[1],
                    "phone_number": result[2]
                }
            return None
    except Exception as e:
        logger.error(f"Failed to get call status: {e}")
        return None


# Initialize the database when the module is imported
try:
    initialize_database()
except Exception as e:
    logger.error(f"Database initialization failed: {e}")