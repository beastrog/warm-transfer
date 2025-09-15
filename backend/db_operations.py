"""
Database operations for the Warm Transfer application.

This module handles all database interactions including call status tracking,
room management, and other persistent data storage.
"""
import os
import json
import sqlite3
from typing import Dict, Optional, Any, List
from datetime import datetime
import logging
from contextlib import contextmanager

# Configure logging
logger = logging.getLogger(__name__)

# Get the directory of the current script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'warm_transfer.db')

# Ensure the database directory exists
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def init_db():
    """Initialize the database with required tables."""
    with db_connection() as conn:
        cursor = conn.cursor()
        
        # Create calls table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            call_sid TEXT UNIQUE NOT NULL,
            room_name TEXT NOT NULL,
            phone_number TEXT NOT NULL,
            status TEXT NOT NULL,
            error TEXT,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create rooms table for tracking room state
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_name TEXT UNIQUE NOT NULL,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create room_members table for tracking room participants
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS room_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_name TEXT NOT NULL,
            identity TEXT NOT NULL,
            role TEXT NOT NULL,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(room_name, identity)
        )
        ''')
        
        # Create indexes for better query performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_calls_room ON calls(room_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_calls_status ON calls(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_room_members_room ON room_members(room_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_room_members_identity ON room_members(identity)')
        
        conn.commit()
        logger.info("Database tables initialized")

@contextmanager
def db_connection():
    """Context manager for database connections with error handling."""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row  # Enable dictionary-style access
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        raise
    finally:
        if conn:
            conn.close()

# Call management functions
def set_call_status(
    call_sid: str = None,
    room_name: str = None,
    status: str = None,
    phone_number: str = None,
    error: str = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Update or create a call status record.
    
    Args:
        call_sid: The Twilio Call SID (required for new records)
        room_name: The room associated with the call (required for new records)
        status: The current call status
        phone_number: The phone number being called
        error: Any error message if the call failed
        metadata: Additional call metadata
        
    Returns:
        The updated call record
    """
    if not call_sid and not room_name:
        raise ValueError("Either call_sid or room_name must be provided")
    
    with db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if we have an existing call for this room
        existing = None
        if room_name:
            cursor.execute(
                'SELECT * FROM calls WHERE room_name = ? ORDER BY created_at DESC LIMIT 1',
                (room_name,)
            )
            existing = cursor.fetchone()
        
        # Prepare metadata
        meta_dict = {}
        if existing and existing['metadata']:
            meta_dict = json.loads(existing['metadata'])
        
        if metadata:
            meta_dict.update(metadata)
        
        meta_json = json.dumps(meta_dict) if meta_dict else None
        
        if existing:
            # Update existing call
            update_fields = []
            params = []
            
            if call_sid and call_sid != existing['call_sid']:
                update_fields.append('call_sid = ?')
                params.append(call_sid)
            
            if status:
                update_fields.append('status = ?')
                params.append(status)
            
            if phone_number:
                update_fields.append('phone_number = ?')
                params.append(phone_number)
            
            if error is not None:
                update_fields.append('error = ?')
                params.append(error)
            
            if meta_json is not None:
                update_fields.append('metadata = ?')
                params.append(meta_json)
            
            if update_fields:
                update_fields.append('updated_at = CURRENT_TIMESTAMP')
                update_sql = f"""
                    UPDATE calls 
                    SET {', '.join(update_fields)}
                    WHERE id = ?
                """
                params.append(existing['id'])
                cursor.execute(update_sql, params)
                
                # Get the updated record
                cursor.execute('SELECT * FROM calls WHERE id = ?', (existing['id'],))
                result = dict(cursor.fetchone())
                logger.debug(f"Updated call status: {result}")
                return result
            
            return dict(existing)
        
        else:
            # Create new call record
            if not call_sid or not room_name:
                raise ValueError("call_sid and room_name are required for new call records")
            
            cursor.execute("""
                INSERT INTO calls (
                    call_sid, room_name, phone_number, status, error, metadata
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                call_sid,
                room_name,
                phone_number or '',
                status or 'initiated',
                error,
                meta_json
            ))
            
            call_id = cursor.lastrowid
            conn.commit()
            
            # Get the newly created record
            cursor.execute('SELECT * FROM calls WHERE id = ?', (call_id,))
            result = dict(cursor.fetchone())
            logger.info(f"Created new call record: {result}")
            return result

def get_call_status(room_name: str = None, call_sid: str = None) -> Optional[Dict[str, Any]]:
    """
    Get the status of a call by room name or call SID.
    
    Args:
        room_name: The room name to look up
        call_sid: The Twilio Call SID to look up
        
    Returns:
        The call record as a dictionary, or None if not found
    """
    if not room_name and not call_sid:
        raise ValueError("Either room_name or call_sid must be provided")
    
    with db_connection() as conn:
        cursor = conn.cursor()
        
        if call_sid:
            cursor.execute(
                'SELECT * FROM calls WHERE call_sid = ? ORDER BY created_at DESC LIMIT 1',
                (call_sid,)
            )
        else:
            cursor.execute(
                'SELECT * FROM calls WHERE room_name = ? ORDER BY created_at DESC LIMIT 1',
                (room_name,)
            )
        
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

# Room management functions
def get_room(room_name: str) -> Optional[Dict[str, Any]]:
    """Get room information by name."""
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM rooms WHERE room_name = ?', (room_name,))
        row = cursor.fetchone()
        return dict(row) if row else None

def create_room(room_name: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a new room or update an existing one."""
    meta_json = json.dumps(metadata) if metadata else None
    
    with db_connection() as conn:
        cursor = conn.cursor()
        
        # Try to insert new room
        try:
            cursor.execute(
                'INSERT INTO rooms (room_name, metadata) VALUES (?, ?)',
                (room_name, meta_json)
            )
            conn.commit()
            logger.info(f"Created new room: {room_name}")
        except sqlite3.IntegrityError:
            # Room already exists, update it
            cursor.execute(
                'UPDATE rooms SET metadata = ?, updated_at = CURRENT_TIMESTAMP WHERE room_name = ?',
                (meta_json, room_name)
            )
            conn.commit()
            logger.debug(f"Updated existing room: {room_name}")
        
        # Return the room data
        cursor.execute('SELECT * FROM rooms WHERE room_name = ?', (room_name,))
        return dict(cursor.fetchone())

# Room member functions
def add_room_member(room_name: str, identity: str, role: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Add a member to a room or update their role/metadata."""
    meta_json = json.dumps(metadata) if metadata else None
    
    with db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if member already exists
        cursor.execute(
            'SELECT * FROM room_members WHERE room_name = ? AND identity = ?',
            (room_name, identity)
        )
        existing = cursor.fetchone()
        
        if existing:
            # Update existing member
            cursor.execute("""
                UPDATE room_members 
                SET role = ?, metadata = ?, updated_at = CURRENT_TIMESTAMP
                WHERE room_name = ? AND identity = ?
            """, (role, meta_json, room_name, identity))
        else:
            # Add new member
            cursor.execute("""
                INSERT INTO room_members (room_name, identity, role, metadata)
                VALUES (?, ?, ?, ?)
            """, (room_name, identity, role, meta_json))
        
        conn.commit()
        
        # Return the updated member record
        cursor.execute(
            'SELECT * FROM room_members WHERE room_name = ? AND identity = ?',
            (room_name, identity)
        )
        return dict(cursor.fetchone())

def get_room_members(room_name: str) -> List[Dict[str, Any]]:
    """Get all members of a room."""
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM room_members WHERE room_name = ?', (room_name,))
        return [dict(row) for row in cursor.fetchall()]

def is_room_member(room_name: str, identity: str) -> bool:
    """Check if a user is a member of a room."""
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT 1 FROM room_members WHERE room_name = ? AND identity = ?',
            (room_name, identity)
        )
        return cursor.fetchone() is not None

# Initialize the database when this module is imported
init_db()
