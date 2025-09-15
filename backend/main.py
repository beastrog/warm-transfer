"""
Warm Transfer Backend API

This module provides the FastAPI application for the Warm Transfer service,
handling WebRTC room management, participant authentication, and Twilio integration.
"""
import os
import uuid
import logging
import time
import asyncio
import threading
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

# FastAPI imports
from fastapi import FastAPI, HTTPException, Depends, Header, BackgroundTasks, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
from services.livekit_client import mint_access_token, validate_room_membership
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

# Thread lock for transfer operations
transfer_locks: Dict[str, threading.Lock] = {}

app = FastAPI(title="Warm Transfer MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
def transfer(req: TransferRequest, background_tasks: BackgroundTasks):
    # Acquire lock for this room to prevent simultaneous transfers
    if req.from_room not in transfer_locks:
        transfer_locks[req.from_room] = threading.Lock()
    
    # Try to acquire the lock with a timeout
    lock_acquired = transfer_locks[req.from_room].acquire(timeout=5)
    if not lock_acquired:
        logger.warning(f"Transfer already in progress for room {req.from_room}")
        raise HTTPException(status_code=409, detail="Transfer already in progress for this room")
    
    # Schedule lock release after response is sent
    background_tasks.add_task(lambda: transfer_locks[req.from_room].release())
    
    to_room = req.to_room or f"room-{uuid.uuid4().hex[:8]}"
    logger.info(f"Transfer request from {req.from_room} to {to_room}")

    if req.transcript and req.transcript.strip():
        transcripts.set_room_transcript(req.from_room, req.transcript.strip())

    # Get transcripts from the database
    existing_transcripts = transcripts.get_room_transcripts(req.from_room)
    existing_transcript = "\n".join(existing_transcripts) if existing_transcripts else ""
    
    try:
        summary_text = generate_summary(existing_transcript or "")
    except Exception as e:
        logger.error(f"Failed to generate summary: {e}")
        # Fallback summary if LLM fails
        first_120_chars = (existing_transcript or "")[:120].replace('\n', ' ').strip()
        summary_text = f"LLM unavailable — Notes: {first_120_chars} — please verify details."

    transcripts.set_room_summary(to_room, summary_text)
    if existing_transcript:
        transcripts.set_room_transcript(to_room, existing_transcript)

    try:
        initiator_token = mint_access_token(room_name=to_room, identity=req.initiator_identity, role="agent")
        target_token = mint_access_token(room_name=to_room, identity=req.target_identity, role="agent")
        caller_identity = os.getenv("CALLER_IDENTITY", "caller")
        caller_token = mint_access_token(room_name=to_room, identity=caller_identity, role="caller")
    except Exception as e:
        logger.error(f"Failed to mint transfer tokens: {e}")
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
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")
TWILIO_TIMEOUT = int(os.getenv("TWILIO_TIMEOUT", "30"))  # Default 30 seconds
MAX_RETRIES = int(os.getenv("TWILIO_MAX_RETRIES", "3"))
TWILIO_RETRY_DELAY = float(os.getenv("TWILIO_RETRY_DELAY", "1.0"))  # Initial delay in seconds

# Twilio client initialization
def get_twilio_client():
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
        logger.error("Twilio credentials not properly configured")
        raise HTTPException(
            status_code=500,
            detail="Twilio service is not properly configured. Please check server logs."
        )
    return TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


@app.post("/twilio-transfer", response_model=TwilioTransferResponse)
async def twilio_transfer(req: TwilioTransferRequest, background_tasks: BackgroundTasks):
    """
    Initiate a warm transfer to an external phone number via Twilio.
    
    This endpoint will:
    1. Validate the request and Twilio configuration
    2. Generate a summary of the current conversation
    3. Initiate a call to the target phone number
    4. Provide the call SID and status for tracking
    
    Returns:
        TwilioTransferResponse with call details and status
    """
    logger.info(f"Initiating Twilio transfer request: {req}")
    
    # Validate room exists and caller is a participant
    try:
        if not validate_room_membership(room_name=req.from_room, identity=req.caller_identity):
            raise HTTPException(
                status_code=403,
                detail=f"Caller {req.caller_identity} is not a member of room {req.from_room}"
            )
    except Exception as e:
        logger.error(f"Membership validation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to validate room membership")
    
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
        
        # Create TwiML with the summary
        twiml = f"""
        <Response>
            <Say voice="Polly.Joanna" language="en-US">
                Hello. You are being connected for a warm transfer. 
                Here's a summary of the conversation so far: {summary_text}
                Please wait while we connect you.
            </Say>
            <Pause length="1"/>
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
                
                call = client.calls.create(
                    to=req.phone_number,
                    from_=TWILIO_PHONE_NUMBER,
                    twiml=twiml,
                    timeout=min(req.timeout_seconds, 60),  # Max 60s for Twilio API
                    status_callback=f"{os.getenv('BASE_URL', '')}/twilio-status",
                    status_events=['initiated', 'ringing', 'answered', 'completed'],
                    status_callback_method='POST'
                )
                
                # Log successful call initiation
                call_duration = time.time() - start_time
                logger.info(
                    f"Twilio call initiated successfully in {call_duration:.2f}s. "
                    f"SID: {call.sid}, Status: {call.status}"
                )
                
                # Store call information for tracking
                set_call_status(
                    room_name=req.from_room,
                    twilio_call_sid=call.sid,
                    status=call.status,
                    phone_number=req.phone_number,
                    metadata={
                        'caller_identity': req.caller_identity,
                        'summary': summary_text[:500],  # Store first 500 chars of summary
                        'attempts': retry_count + 1,
                        'duration_seconds': call_duration
                    }
                )
                
                # Schedule background task to check call status
                background_tasks.add_task(
                    check_call_status_async,
                    call_sid=call.sid,
                    room_name=req.from_room,
                    max_attempts=12  # Check for up to 1 minute (5s intervals)
                )
                
                return TwilioTransferResponse(
                    call_sid=call.sid,
                    to_number=req.phone_number,
                    status=call.status
                )
                
            except Exception as e:
                retry_count += 1
                last_error = str(e)
                logger.warning(
                    f"Twilio call attempt {retry_count} failed: {e}"
                )
                
                if retry_count >= MAX_RETRIES:
                    break
                    
                # Exponential backoff with jitter
                delay = min(
                    TWILIO_RETRY_DELAY * (2 ** (retry_count - 1)),
                    30  # Max 30 seconds between retries
                )
                time.sleep(delay)
        
        # If we get here, all retries failed
        error_msg = f"All {MAX_RETRIES} Twilio call attempts failed: {last_error}"
        logger.error(error_msg)
        
        # Log the failure for analytics
        set_call_status(
            room_name=req.from_room,
            status="failed",
            phone_number=req.phone_number,
            error=last_error,
            metadata={
                'caller_identity': req.caller_identity,
                'attempts': retry_count,
                'duration_seconds': time.time() - start_time
            }
        )
        
        raise HTTPException(
            status_code=500,
            detail=error_msg
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions with proper status codes
        raise
        
    except Exception as e:
        # Catch-all for any other exceptions
        error_msg = f"Unexpected error during Twilio transfer: {e}"
        logger.exception(error_msg)
        raise HTTPException(
            status_code=500,
            detail=error_msg
        )
        
    finally:
        # Clean up any resources if needed
        pass


async def check_call_status_async(call_sid: str, room_name: str, max_attempts: int = 12):
    """
    Background task to periodically check the status of a Twilio call.
    
    Args:
        call_sid: The Twilio Call SID to check
        room_name: The room associated with the call
        max_attempts: Maximum number of status checks to perform
    """
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
            set_call_status(
                room_name=room_name,
                twilio_call_sid=call_sid,
                status=call.status,
                metadata={
                    'last_checked': time.time(),
                    'attempt': attempt,
                    'call_duration': call.duration if hasattr(call, 'duration') else None
                }
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
        set_call_status(
            twilio_call_sid=call_sid,
            status=call_status,
            metadata={
                'last_updated': time.time(),
                'call_duration': form_data.get('CallDuration'),
                'direction': form_data.get('Direction'),
                'from_number': form_data.get('From'),
                'to_number': form_data.get('To'),
                'caller_name': form_data.get('CallerName'),
                'caller_country': form_data.get('CallerCountry')
            }
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
