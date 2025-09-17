"""
Warm Transfer Backend API

This module provides the FastAPI application for the Warm Transfer service,
handling WebRTC room management, participant authentication, and Twilio integration.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Verify required environment variables are set
required_vars = [
    'LIVEKIT_API_KEY',
    'LIVEKIT_API_SECRET',
    'LIVEKIT_URL',
    'GROQ_API_KEY',
    'TWILIO_ACCOUNT_SID',
    'TWILIO_AUTH_TOKEN',
    'TWILIO_PHONE_NUMBER'
]

for var in required_vars:
    if not os.getenv(var):
        print(f"Warning: Required environment variable {var} is not set")
import uuid
import os
import time
import logging
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any

# Third-party imports
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Header, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from contextlib import asynccontextmanager
import logging
from typing import Dict, Any
import os


# Import LLM client to check its status
from services.llm_client import GROQ_AVAILABLE, GROQ_API_KEY

# Configure logging with debug level
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)

# Get logger instance
logger = logging.getLogger(__name__)

# Configure specific loggers
loggers = {
    'twilio': logging.DEBUG,
    'livekit': logging.DEBUG,
    'aiohttp': logging.DEBUG,
    'asyncio': logging.DEBUG,
    'websockets': logging.INFO,  # Less verbose
    'urllib3': logging.INFO,     # Less verbose
    'PIL': logging.INFO,         # Less verbose
    'matplotlib': logging.INFO   # Less verbose
}

for log_name, level in loggers.items():
    logging.getLogger(log_name).setLevel(level)

logger.debug("Debug logging enabled")

# Initialize FastAPI app
app = FastAPI(title="Warm Transfer MVP")

# Register health check endpoint at the root level
@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint that verifies backend and LLM status"""
    llm_status = {
        "available": False,
        "provider": "groq",
        "model": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        "error": None
    }
    
    # Check if LLM is properly configured
    if not GROQ_AVAILABLE:
        llm_status["error"] = "Groq SDK not installed"
    elif not GROQ_API_KEY:
        llm_status["error"] = "GROQ_API_KEY not configured"
    else:
        llm_status["available"] = True
    
    return {
        "status": "ok",
        "llm": llm_status,
        "version": "1.0.0"
    }

# Debug: Print all routes
print("\nRegistered routes:")
for route in app.routes:
    if hasattr(route, 'path'):
        print(f"- {route.path}")
    elif hasattr(route, 'routes'):
        for r in route.routes:
            print(f"- {r.path}")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    expose_headers=["*"]
)


# Twilio imports
from twilio.rest import Client as TwilioClient
from twilio.base.exceptions import TwilioRestException

# Import models
from models import (
    CreateRoomRequest, CreateRoomResponse,
    JoinTokenRequest, JoinTokenResponse,
    TransferRequest, TransferResponse,
    RoomSummaryResponse, TwilioTransferRequest,
    TwilioTransferResponse, ValidateMembershipRequest,
    ValidateMembershipResponse
)

# Import services and database operations
import transcripts
from services.livekit_client import mint_access_token, validate_room_membership, disconnect_participant
from services.llm_client import generate_summary
from db_operations import (
    set_call_status, get_call_status,
    create_room as db_create_room,
    add_room_member, get_room_members,
    is_room_member
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEBUG") == "true" else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Thread lock for transfer operations with timeouts
from threading import Lock, Timer, RLock
from typing import Dict, Optional, Set
from datetime import datetime, timedelta

# Room state management
class RoomState:
    def __init__(self):
        self._lock = RLock()
        self._rooms: Dict[str, Dict] = {}  # room_name -> state
        self._room_creation_time: Dict[str, datetime] = {}
        self._room_timeout = timedelta(hours=1)  # Room timeout

    def create_room(self, room_name: str, initial_state: Optional[dict] = None):
        with self._lock:
            if room_name not in self._rooms:
                self._rooms[room_name] = initial_state or {}
                self._room_creation_time[room_name] = datetime.utcnow()
                logger.info(f"Created room {room_name} with state: {initial_state}")
                return True
            return False

    def get_room_state(self, room_name: str) -> Optional[dict]:
        with self._lock:
            return self._rooms.get(room_name)

    def update_room_state(self, room_name: str, updates: dict) -> bool:
        with self._lock:
            if room_name in self._rooms:
                self._rooms[room_name].update(updates)
                logger.debug(f"Updated room {room_name} state: {updates}")
                return True
            return False

    def remove_room(self, room_name: str) -> bool:
        with self._lock:
            if room_name in self._rooms:
                del self._rooms[room_name]
                if room_name in self._room_creation_time:
                    del self._room_creation_time[room_name]
                logger.info(f"Removed room {room_name}")
                return True
            return False

    def cleanup_stale_rooms(self) -> int:
        """Remove rooms that have exceeded their timeout"""
        removed = 0
        now = datetime.utcnow()
        
        with self._lock:
            stale_rooms = [
                room for room, created in self._room_creation_time.items()
                if now - created > self._room_timeout
            ]
            
            for room in stale_rooms:
                self.remove_room(room)
                removed += 1
                
        if removed > 0:
            logger.info(f"Cleaned up {removed} stale rooms")
            
        return removed

# Global room state manager
room_state_manager = RoomState()

# Transfer lock management
transfer_locks: Dict[str, Lock] = {}
LOCK_TIMEOUT = 30  # seconds

def release_lock(room_name: str):
    """Release the transfer lock for a room if it exists"""
    if room_name in transfer_locks:
        try:
            transfer_locks[room_name].release()
            logger.debug(f"Released lock for room {room_name}")
        except Exception as e:
            logger.warning(f"Error releasing lock for room {room_name}: {e}")
            # Lock might already be released

# Background task to clean up stale rooms
async def cleanup_stale_rooms_task():
    """Background task to clean up stale rooms"""
    while True:
        try:
            removed = room_state_manager.cleanup_stale_rooms()
            if removed > 0:
                logger.info(f"Cleaned up {removed} stale rooms")
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}", exc_info=True)
        
        # Sleep for 5 minutes between cleanups
        await asyncio.sleep(300)  # 5 minutes

# Start the cleanup task when the app starts
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(cleanup_stale_rooms_task())
    logger.info("Started background cleanup task")

# App initialization moved to the top of the file

# Test endpoint to verify LLM functionality
@app.get("/test-llm", response_class=PlainTextResponse)
async def test_llm():
    from services.llm_client import generate_summary
    
    test_text = """
    Caller: Hi, I'm having trouble with my internet connection.
    Agent: I can help with that. Have you tried restarting your router?
    Caller: Yes, I've tried that but it's still not working.
    Agent: Let's check your network settings. Can you tell me what lights are on your router?
    """
    
    try:
        logger.info("Testing LLM with sample conversation...")
        result = generate_summary(test_text)
        logger.info(f"LLM test successful. Result: {result}")
        return f"LLM Test Successful!\n\nSummary:\n{result}"
    except Exception as e:
        logger.error(f"LLM test failed: {str(e)}", exc_info=True)
        return f"LLM Test Failed!\n\nError: {str(e)}\n\nPlease check the backend logs for more details."

# Authentication is disabled for assessment purposes
def verify_api_key():
    return True


@app.post("/create-room", response_model=CreateRoomResponse)
def create_room(req: CreateRoomRequest):
    room_name = req.room_name or f"room-{uuid.uuid4().hex[:8]}"
    try:
        logger.info(f"Creating room: {room_name} for identity: {req.identity}")
        token = mint_access_token(room_name=room_name, identity=req.identity, role=req.role)
    except Exception as e:
        logger.error(f"Failed to create room/token: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create room/token: {e}")
    return CreateRoomResponse(room_name=room_name, token=token)


@app.post("/join-token", response_model=JoinTokenResponse)
def join_token(req: JoinTokenRequest):
    try:
        logger.info(f"Generating join token for room: {req.room_name}, identity: {req.identity}")
        token = mint_access_token(room_name=req.room_name, identity=req.identity, role="participant")
    except Exception as e:
        logger.error(f"Failed to mint token: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to mint token: {e}")
    return JoinTokenResponse(token=token)


@app.post("/transfer", response_model=TransferResponse)
async def transfer(req: TransferRequest, background_tasks: BackgroundTasks):
    """
    Handle warm transfer between rooms with proper participant management.
    
    This endpoint:
    1. Validates the transfer request
    2. Creates a new room for the transfer
    3. Generates tokens for all participants
    4. Transfers call context and transcripts
    5. Manages room state and locking
    """
    logger.info(f"Received transfer request: {req}")
    start_time = time.time()
    
    def log_duration():
        duration = time.time() - start_time
        logger.info(f"Transfer request completed in {duration:.2f} seconds")
        
    async def cleanup_on_error(room_name: str):
        """Clean up resources if an error occurs during transfer."""
        try:
            if room_name in room_state_manager._rooms:
                room_state_manager.update_room_state(room_name, {
                    "status": "error",
                    "error_time": datetime.utcnow().isoformat()
                })
                logger.warning(f"Cleaned up room state for {room_name} due to error")
        except Exception as e:
            logger.error(f"Error during cleanup for {room_name}: {e}", exc_info=True)
    
    # Register cleanup to log duration
    background_tasks.add_task(log_duration)
    
    # Initialize variables for cleanup
    to_room = None
    
    try:
        # Validate request
        if not req.from_room:
            error_msg = "Source room name is required"
            logger.error(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
        
        if not req.initiator_identity or not req.target_identity:
            error_msg = "Initiator and target identities are required"
            logger.error(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Acquire lock for this room to prevent simultaneous transfers
        with transfer_locks.setdefault(req.from_room, Lock()):
            logger.info(f"Acquired transfer lock for room: {req.from_room}")
            
            # Use the same room for the transfer
            to_room = req.from_room
            logger.info(f"Initiating transfer in room: {to_room}")
                
            try:
                # Update the existing room state
                room_state = room_state_manager.get_room_state(to_room)
                if not room_state:
                    room_state_manager.create_room(to_room, {
                        "status": "active",
                        "created_at": datetime.utcnow().isoformat(),
                        "participants": [req.initiator_identity, req.target_identity],
                        "transfer_initiated_at": datetime.utcnow().isoformat(),
                        "initiator": req.initiator_identity,
                        "target": req.target_identity
                    })
                
                # Store any provided transcript updates
                if req.transcript and req.transcript.strip():
                    logger.debug(f"Updating transcript for room {to_room}")
                    transcripts.set_room_transcript(to_room, req.transcript.strip())
                
                # Get existing transcripts
                logger.debug(f"Retrieving existing transcripts for room {to_room}")
                existing_transcripts = transcripts.get_room_transcripts(to_room)
                existing_transcript = "\n".join(existing_transcripts) if existing_transcripts else ""
                
                # Generate summary using LLM or fallback to a simple summary
                summary_text = ""
                try:
                    logger.info("Generating call summary...")
                    summary_text = generate_summary(existing_transcript or "")
                    logger.debug(f"Generated summary: {summary_text[:100]}...")
                except Exception as e:
                    error_msg = f"Failed to generate summary: {e}"
                    logger.error(error_msg, exc_info=True)
                    # Fallback summary if LLM fails
                    first_120_chars = (existing_transcript or "")[:120].replace('\n', ' ').strip()
                    summary_text = f"LLM unavailable — Notes: {first_120_chars} — please verify details."
                    logger.warning(f"Using fallback summary: {summary_text}")
                
                # Update the room with transfer information
                room_state_manager.update_room_state(to_room, {
                    "status": "transferring",
                    "transfer_initiated_at": datetime.utcnow().isoformat(),
                    "initiator": req.initiator_identity,
                    "target": req.target_identity,
                    "summary": summary_text
                })
                
                try:
                    # Store summary and transcript in the room
                    logger.debug(f"Storing summary and transcript in room: {to_room}")
                    transcripts.set_room_summary(to_room, summary_text)
                    if existing_transcript:
                        transcripts.set_room_transcript(to_room, existing_transcript)
                    
                    # Generate tokens for all participants
                    logger.info("Generating participant tokens...")
                    
                    # Token for the initiator (Agent A) - stays in the same room
                    initiator_token = mint_access_token(
                        room_name=to_room, 
                        identity=req.initiator_identity, 
                        role="agent"
                    )
                    
                    # Token for the target agent (Agent B) - joins the same room
                    target_token = mint_access_token(
                        room_name=to_room, 
                        identity=req.target_identity, 
                        role="agent"
                    )
                    
                    # Token for the caller (already in the room)
                    caller_identity = os.getenv("CALLER_IDENTITY", "caller")
                    caller_token = mint_access_token(
                        room_name=to_room, 
                        identity=caller_identity, 
                        role="caller"
                    )           # Log the transfer for auditing
                    logger.info(f"Transfer setup complete: {req.from_room} -> {to_room}")
                    
                    # Prepare response
                    return TransferResponse(
                        to_room=to_room,  # Same as from_room since we're using the same room
                        initiator_token=initiator_token,
                        target_token=target_token,
                        caller_token=caller_token,
                        summary=summary_text,
                    )
                    
                    logger.debug("Transfer response prepared successfully")
                    return response
                    
                except Exception as e:
                    error_msg = f"Failed to complete transfer setup: {e}"
                    logger.error(error_msg, exc_info=True)
                    # Clean up the new room if it was created
                    if to_room and to_room in room_state_manager._rooms:
                        await cleanup_on_error(to_room)
                    raise HTTPException(status_code=500, detail=error_msg)
                    
            except Exception as e:
                error_msg = f"Transfer failed: {e}"
                logger.error(error_msg, exc_info=True)
                
                # Clean up any created resources
                if to_room:
                    await cleanup_on_error(to_room)
                if req.from_room in room_state_manager._rooms:
                    await cleanup_on_error(req.from_room)
                    
        raise
        
    except Exception as e:
        error_msg = f"Unexpected error during transfer: {e}"
        logger.error(error_msg, exc_info=True)
        
        # Clean up any created resources
        if to_room:
            await cleanup_on_error(to_room)
        if req.from_room in room_state_manager._rooms:
            await cleanup_on_error(req.from_room)
            
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during transfer. Please try again."
        )
        
    finally:
        # Always ensure the lock is released
        if req.from_room in transfer_locks and transfer_locks[req.from_room].locked():
            try:
                transfer_locks[req.from_room].release()
                logger.info(f"Released transfer lock for room: {req.from_room}")
            except Exception as e:
                logger.error(f"Error releasing lock for room {req.from_room}: {e}", exc_info=True)
                
@app.get("/room/{room_name}/summary", response_model=RoomSummaryResponse)
def room_summary(room_name: str):
    logger.info(f"Fetching summary for room: {room_name}")
    
    # Get transcripts from the database
    existing_transcripts = transcripts.get_room_transcripts(room_name)
    existing_transcript = "\n".join(existing_transcripts) if existing_transcripts else ""
    
    return RoomSummaryResponse(
        summary=transcripts.get_room_summary(room_name) or "",
        transcript=existing_transcript or "",
    )


@app.post("/validate-membership", response_model=ValidateMembershipResponse)
def validate_membership(req: ValidateMembershipRequest):
    logger.info(f"Validating membership for {req.identity} in room {req.room_name}")
    try:
        is_member = validate_room_membership(room_name=req.room_name, identity=req.identity)
        if is_member:
            return ValidateMembershipResponse(
                is_member=True,
                message=f"User {req.identity} is a member of room {req.room_name}"
            )
        else:
            return ValidateMembershipResponse(
                is_member=False,
                message=f"User {req.identity} is not a member of room {req.room_name}"
            )
    except Exception as e:
        logger.error(f"Error validating membership: {e}")
        # Fallback to checking ROOM_STORE
        room_data = transcripts.ROOM_STORE.get(req.room_name, {})
        if room_data.get("members", {}).get(req.identity):
            return ValidateMembershipResponse(
                is_member=True,
                message=f"User {req.identity} is a member of room {req.room_name} (from store)"
            )
        return ValidateMembershipResponse(
            is_member=False,
            message=f"Could not validate membership: {e}"
        )


# --- Twilio Integration ---
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
TWILIO_TIMEOUT = int(os.getenv("TWILIO_TIMEOUT", "30"))  # Default 30 seconds
MAX_RETRIES = int(os.getenv("TWILIO_MAX_RETRIES", "3"))
TWILIO_RETRY_DELAY = float(os.getenv("TWILIO_RETRY_DELAY", "1.0"))  # Initial delay in seconds

# Flag to track if Twilio is properly configured
TWILIO_ENABLED = all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER])
if not TWILIO_ENABLED:
    logger.warning("""
        Twilio is not properly configured. To enable phone transfers, set these environment variables:
        - TWILIO_ACCOUNT_SID
        - TWILIO_AUTH_TOKEN
        - TWILIO_PHONE_NUMBER
    """)

def check_twilio_config():
    """Check if Twilio is properly configured and enabled."""
    if not TWILIO_ENABLED:
        raise HTTPException(
            status_code=501,  # Not Implemented
            detail=(
                "Phone transfers are not currently available. "
                "The system is not configured with Twilio credentials. "
                "Please contact the administrator."
            )
        )

# Twilio client initialization
def get_twilio_client():
    check_twilio_config()
    return TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


@app.post("/twilio-transfer", response_model=TwilioTransferResponse)
async def twilio_transfer(req: TwilioTransferRequest, background_tasks: BackgroundTasks):
    """
    Initiate a warm transfer to an external phone number via Twilio.
    
    This endpoint will:
    1. Validate the request and Twilio configuration
    2. Generate a summary of the current conversation
    3. Initiate a call to the target phone number and connect to the existing room
    4. Disconnect Agent A after the summary is played
    5. Keep the caller and Twilio call recipient connected
    
    Returns:
        TwilioTransferResponse with call details and status
    """
    try:
        # Check Twilio configuration before proceeding
        check_twilio_config()
        
        logger.info(f"Initiating Twilio transfer request: {req.dict()}")
        
        # Validate room exists and caller is a participant
        try:
            if not validate_room_membership(room_name=req.from_room, identity=req.caller_identity):
                logger.error(f"Caller {req.caller_identity} is not a member of room {req.from_room}")
                raise HTTPException(
                    status_code=403,
                    detail={"error": "forbidden", "message": f"Caller is not a member of room {req.from_room}"}
                )
        except Exception as e:
            logger.error(f"Membership validation failed: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500, 
                detail={"error": "validation_failed", "message": "Failed to validate room membership"}
            )
        
        # Get conversation transcript
        try:
            existing_transcripts = transcripts.get_room_transcripts(req.from_room)
            existing_transcript = "\n".join(existing_transcripts) if existing_transcripts else ""
            
            # Generate summary with fallback if LLM fails
            try:
                summary_text = generate_summary(existing_transcript)
                logger.debug(f"Generated summary: {summary_text[:100]}...")
            except Exception as e:
                logger.warning(f"LLM summary generation failed, using fallback: {e}")
                first_120_chars = existing_transcript[:120].replace('\n', ' ').strip() \
                    if existing_transcript else "No transcript available"
                summary_text = f"LLM unavailable — Notes: {first_120_chars} — please verify details."
            
            # Generate a unique identity for the Twilio participant
            twilio_identity = f"twilio-{str(uuid.uuid4())[:8]}"
            
            # Generate a token for the Twilio participant to join the existing room
            twilio_token = mint_access_token(
                room_name=req.from_room,
                identity=twilio_identity,
                role="agent"
            )
            
            # Create TwiML that will connect the call to the existing LiveKit room
            twiml = f"""
            <Response>
                <Say voice="Polly.Joanna" language="en-US">
                    Hello. You are being connected for a warm transfer. 
                    Here's a summary of the conversation so far: {summary_text}
                    Please wait while we connect you to the call.
                </Say>
                <Connect>
                    <Room participantIdentity="{twilio_identity}">{req.from_room}</Room>
                </Connect>
            </Response>
            """.strip()
            
            # Get Twilio client with validation
            client = get_twilio_client()
            
            # Track call attempt metrics
            start_time = time.time()
            retry_count = 0
            last_error = None
            
            # Implement retry with exponential backoff
            while retry_count < MAX_RETRIES:
                try:
                    logger.info(f"Initiating Twilio call to {req.phone_number} (attempt {retry_count + 1}/{MAX_RETRIES})")
                    
                    # Get base URL for callbacks
                    base_url = os.getenv('BASE_URL', '').strip()
                    if not base_url:
                        logger.warning("BASE_URL environment variable not set, using default")
                    
                    call = client.calls.create(
                        to=req.phone_number,
                        from_=TWILIO_PHONE_NUMBER,
                        twiml=twiml,
                        timeout=min(getattr(req, 'timeout_seconds', 30), 60),  # Default 30s, max 60s for Twilio API
                        status_callback=f"{base_url}/twilio-status" if base_url else None,
                        status_callback_method='POST',
                        status_callback_event=['initiated', 'ringing', 'answered', 'completed']
                    )
                    
                    # Log successful call initiation
                    call_duration = time.time() - start_time
                    logger.info(
                        f"Twilio call initiated successfully in {call_duration:.2f}s. "
                        f"SID: {call.sid}, Status: {call.status}"
                    )
                    
                    # Store call information for tracking
                    from services.database import set_call_status
                    set_call_status(
                        room_name=req.from_room,
                        twilio_call_sid=call.sid,
                        status=call.status,
                        phone_number=req.phone_number
                    )
                    
                    # Start background task to monitor call status and handle agent transfer
                    background_tasks.add_task(
                        handle_agent_transfer,
                        call_sid=call.sid,
                        room_name=req.from_room,
                        agent_identity=req.caller_identity,
                        twilio_identity=twilio_identity,
                        summary=summary_text
                    )
                    
                    return TwilioTransferResponse(
                        call_sid=call.sid,
                        to_number=req.phone_number,
                        status=call.status
                    )
                    
                except TwilioRestException as e:
                    last_error = e
                    retry_count += 1
                    if retry_count < MAX_RETRIES:
                        wait_time = TWILIO_RETRY_DELAY * (2 ** (retry_count - 1))
                        logger.warning(
                            f"Twilio call attempt {retry_count} failed. "
                            f"Retrying in {wait_time:.1f}s. Error: {str(e)}"
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(
                            f"All {MAX_RETRIES} Twilio call attempts failed. "
                            f"Last error: {str(e)}", 
                            exc_info=True
                        )
                        raise HTTPException(
                            status_code=500,
                            detail={
                                "error": "call_initiation_failed",
                                "message": f"Failed to initiate call after {MAX_RETRIES} attempts",
                                "twilio_error": str(e)
                            }
                        )
                        
                except Exception as e:
                    logger.error(
                        f"Unexpected error during Twilio call initiation: {str(e)}", 
                        exc_info=True
                    )
                    raise HTTPException(
                        status_code=500,
                        detail={
                            "error": "unexpected_error",
                            "message": "An unexpected error occurred while initiating the call",
                            "details": str(e)
                        }
                    )
                    
        except Exception as e:
            logger.error(f"Failed to process transcript: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "transcript_processing_error",
                    "message": "Failed to process call transcript"
                }
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions as they are already properly formatted
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error in twilio_transfer: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_server_error",
                "message": f"An unexpected error occurred: {str(e)}"
            }
        )


async def handle_agent_transfer(call_sid: str, room_name: str, agent_identity: str, twilio_identity: str, summary: str, max_attempts: int = 12):
    """
    Background task to handle the agent transfer process.

    Args:
        call_sid: The Twilio Call SID to check
        room_name: The room where the transfer is happening
        agent_identity: The identity of Agent A who initiated the transfer
        twilio_identity: The identity of the Twilio call participant
        summary: The conversation summary that was shared
        max_attempts: Maximum number of status checks to perform
    """
    logger.info(f"Starting agent transfer process for call {call_sid} in room {room_name}")

    # Wait a moment for the Twilio call to be established
    await asyncio.sleep(5)

    # Disconnect Agent A
    try:
        logger.info(f"Attempting to disconnect agent {agent_identity} from room {room_name}")
        success = await disconnect_participant(room_name, agent_identity)
        if success:
            logger.info(f"Successfully disconnected agent {agent_identity} from room {room_name}")
        else:
            logger.warning(f"Failed to disconnect agent {agent_identity} from room {room_name}")
            # Continue even if disconnection fails, as the transfer can still proceed
    except Exception as e:
        logger.error(f"Error disconnecting agent {agent_identity}: {str(e)}")
        # Continue with the transfer even if disconnection fails

    # Monitor the Twilio call status
    # Monitor the call status
    attempt = 0
    while attempt < max_attempts:
        try:
            # Get the latest call status from Twilio
            client = get_twilio_client()
            call = client.calls(call_sid).fetch()
            
            # Update our database with the latest status
            from services.database import set_call_status
            set_call_status(
                room_name=room_name,
                twilio_call_sid=call_sid,
                status=call.status,
                phone_number=''  # We don't have the phone number in this context
            )
            
            # If call is completed/failed, we can stop checking
            if call.status in ['completed', 'failed', 'busy', 'no-answer', 'canceled']:
                logger.info(f"Call {call_sid} ended with status: {call.status}")
                return
                
        except Exception as e:
            logger.warning(f"Error checking call status (attempt {attempt}/{max_attempts}): {e}")
            
        # Wait before next check (with increasing delay)
        await asyncio.sleep(min(5 * (attempt + 1), 30))  # Max 30s between checks
        attempt += 1
    
    logger.warning(f"Reached max status check attempts for call {call_sid}")
    if not call_sid or not room_name:
        logger.warning("Missing call_sid or room_name for status check")
        return
    
    attempt = 0
    while attempt < max_attempts:
        attempt += 1
        try:
            # Get the latest call status from Twilio
            client = get_twilio_client()
            call = client.calls(call_sid).fetch()
            
# Update our database with the latest status
            from services.database import set_call_status
            set_call_status(
                room_name=room_name,
                twilio_call_sid=call_sid,
                status=call.status,
                phone_number=''  # We don't have the phone number in this context
            )
            
            # If call is completed/failed, we can stop checking
            if call.status in ['completed', 'failed', 'busy', 'no-answer', 'canceled']:
                logger.info(f"Call {call_sid} ended with status: {call.status}")
                return
                
        except Exception as e:
            logger.warning(f"Error checking call status (attempt {attempt}/{max_attempts}): {e}")
            
        # Wait before next check (with increasing delay)
        await asyncio.sleep(min(5 * attempt, 30))  # Max 30s between checks
    
    logger.warning(f"Reached max status check attempts for call {call_sid}")


@app.post("/twilio-status")
async def twilio_status_webhook(request: Request):
    """Webhook endpoint for Twilio to report call status changes."""
    try:
        form_data = await request.form()
        call_sid = form_data.get('CallSid')
        call_status = form_data.get('CallStatus')
        
        if not call_sid or not call_status:
            logger.warning("Missing CallSid or CallStatus in Twilio webhook")
            return {"status": "error", "message": "Missing required parameters"}
        
# Update our database with the latest status
        from services.database import set_call_status
        set_call_status(
            room_name=call_sid,  # Using call_sid as room_name since we don't have the room name
            twilio_call_sid=call_sid,
            status=call_status,
            phone_number=''  # We don't have the phone number in this context
        )
        
        logger.info(f"Updated call {call_sid} status to {call_status}")
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Error processing Twilio webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/twilio-call-status/{room_name}")
async def get_twilio_call_status(room_name: str, background_tasks: BackgroundTasks):
    """
    Get the status of a Twilio call for a specific room.
    
    This endpoint will return the current status of the call from our database,
    and optionally trigger a background refresh from Twilio if requested.
    """
    try:
        call_status = get_call_status(room_name)
        if not call_status or not call_status.get("twilio_call_sid"):
            return {
                "status": "not_found",
                "message": f"No active call found for room {room_name}"
            }
        
        # If the call is still active, trigger a background refresh
        if call_status.get("status") in ['queued', 'initiated', 'ringing', 'in-progress']:
            background_tasks.add_task(
                check_call_status_async,
                call_sid=call_status["twilio_call_sid"],
                room_name=room_name,
                max_attempts=1  # Just check once in the background
            )
        
        # Return the current status from our database
        return {
            "status": call_status.get("status", "unknown"),
            "call_sid": call_status.get("twilio_call_sid"),
            "phone_number": call_status.get("phone_number"),
            "last_updated": call_status.get("updated_at"),
            "metadata": call_status.get("metadata", {})
        }
        
    except Exception as e:
        logger.error(f"Error getting Twilio call status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get call status: {str(e)}"
        )
