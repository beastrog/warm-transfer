from pydantic import BaseModel, Field, validator, constr
from typing import Optional, List, Dict, Any
import re
from datetime import datetime


class CreateRoomRequest(BaseModel):
    room_name: Optional[str] = None
    identity: constr(min_length=1, max_length=50)
    role: str
    
    @validator('role')
    def validate_role(cls, v):
        if v not in ['agent', 'caller', 'participant']:
            raise ValueError('Role must be one of: agent, caller, participant')
        return v
        
    @validator('identity')
    def validate_identity(cls, v):
        if not v or not v.strip():
            raise ValueError('Identity cannot be empty or whitespace')
        return v.strip()


class CreateRoomResponse(BaseModel):
    room_name: str
    token: str


class JoinTokenRequest(BaseModel):
    room_name: str = Field(..., min_length=1)
    identity: str = Field(..., min_length=1, max_length=50)
    
    @validator('room_name', 'identity')
    def validate_fields(cls, v):
        if not v.strip():
            raise ValueError('Field cannot be empty or whitespace')
        return v


class JoinTokenResponse(BaseModel):
    token: str


class TransferRequest(BaseModel):
    from_room: constr(min_length=1)
    to_room: Optional[str] = None
    initiator_identity: constr(min_length=1, max_length=50)
    target_identity: constr(min_length=1, max_length=50)
    transcript: Optional[str] = ""
    
    @validator('from_room', 'initiator_identity', 'target_identity')
    def validate_fields(cls, v):
        if not v or not v.strip():
            raise ValueError('Field cannot be empty or whitespace')
        return v.strip()


class TransferResponse(BaseModel):
    to_room: str
    initiator_token: str
    target_token: str
    caller_token: str
    summary: str


class RoomSummaryResponse(BaseModel):
    summary: str
    transcript: str


class TwilioTransferRequest(BaseModel):
    """Request model for initiating a Twilio transfer.
    
    Attributes:
        from_room: The room name to transfer from (required)
        phone_number: Phone number in E.164 format (e.g., +12125551234)
        caller_identity: Identity of the caller initiating the transfer (required)
        timeout_seconds: Optional timeout for the call in seconds (default: 30)
    """
    from_room: str = Field(..., min_length=1, description="The name of the room to transfer from")
    phone_number: str = Field(..., min_length=10, max_length=20, description="Phone number in E.164 format")
    caller_identity: str = Field(..., min_length=1, max_length=50, description="Identity of the caller initiating the transfer")
    timeout_seconds: int = Field(30, ge=10, le=300, description="Call timeout in seconds (10-300)")
    
    @validator('phone_number')
    def validate_phone_number(cls, v):
        if not v:
            raise ValueError('Phone number is required')
            
        # Remove all non-digit characters except leading +
        cleaned = re.sub(r'[^\d+]', '', v)
        
        # Ensure it starts with + and has at least 10 digits
        if not re.match(r'^\+[1-9]\d{1,14}$', cleaned):
            raise ValueError(
                'Phone number must be in E.164 format (e.g., +12125551234). ' \
                'Must start with + followed by country code and number.'
            )
            
        # Additional validation for country code and length
        if len(cleaned) < 11:  # +1 (country code) + 10 digits
            raise ValueError('Phone number too short')
            
        if len(cleaned) > 16:  # + and up to 15 digits
            raise ValueError('Phone number too long')
            
        return cleaned
        
    @validator('from_room', 'caller_identity')
    def validate_required_fields(cls, v):
        if not v or not v.strip():
            raise ValueError('This field cannot be empty')
        return v.strip()
    


class TwilioTransferResponse(BaseModel):
    call_sid: str
    to_number: str
    status: str


class ValidateMembershipRequest(BaseModel):
    room_name: str = Field(..., min_length=1)
    identity: str = Field(..., min_length=1, max_length=50)
    
    @validator('room_name', 'identity')
    def validate_fields(cls, v):
        if not v or not v.strip():
            raise ValueError('Field cannot be empty or whitespace')
        return v.strip()


class ValidateMembershipResponse(BaseModel):
    is_member: bool
    message: str