import os
import time
import logging
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
import jwt
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Load env from a local .env if present
load_dotenv()

logger = logging.getLogger(__name__)

LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "")

# Configure requests with retry logic
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET", "POST"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
http = requests.Session()
http.mount("https://", adapter)
http.mount("http://", adapter)

# Default timeout for API calls (in seconds)
DEFAULT_TIMEOUT = int(os.getenv("API_TIMEOUT", "10"))


def mint_access_token(*, room_name: str, identity: str, role: Optional[str] = None, ttl_seconds: int = 3600) -> str:
    """Generate a JWT token for LiveKit room access with limited privileges."""
    if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
        logger.error("LiveKit API credentials not configured")
        raise RuntimeError("LIVEKIT_API_KEY and LIVEKIT_API_SECRET must be set")

    now = int(time.time())
    
    # Define permissions based on role
    video_grant: Dict[str, Any] = {
        "room": room_name,
        "roomJoin": True,
    }
    
    # Add specific permissions based on role
    if role == "agent":
        video_grant.update({
            "canPublish": True,
            "canSubscribe": True,
            "canPublishData": True,
        })
    elif role == "caller":
        video_grant.update({
            "canPublish": True,
            "canSubscribe": True,
            "canPublishData": False,
        })
    else:  # participant or other roles
        video_grant.update({
            "canPublish": True,
            "canSubscribe": True,
            "canPublishData": False,
        })
    
    payload = {
        "iss": LIVEKIT_API_KEY,
        "nbf": now,
        "exp": now + ttl_seconds,
        "sub": identity,
        "video": video_grant,
    }
    
    try:
        token = jwt.encode(payload, LIVEKIT_API_SECRET, algorithm="HS256")
        if isinstance(token, bytes):
            token = token.decode("utf-8")
        logger.debug(f"Generated token for {identity} in room {room_name}")
        return token
    except Exception as e:
        logger.error(f"Failed to generate token: {e}")
        raise


def validate_room_membership(*, room_name: str, identity: str) -> bool:
    """Validate if a user is a member of a LiveKit room."""
    if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET or not LIVEKIT_URL:
        logger.error("LiveKit API credentials or URL not configured")
        raise RuntimeError("LiveKit credentials not fully configured")
    
    # For LiveKit Cloud, we'd use their Admin API
    # For self-hosted, we'd need to implement this based on their API
    # This is a simplified implementation
    
    try:
        # Create an admin token with room list permissions
        admin_token = mint_admin_token()
        
        # Extract the server URL from the WebSocket URL
        server_url = LIVEKIT_URL.replace("wss://", "https://").replace("ws://", "http://")
        if server_url.endswith("/"):
            server_url = server_url[:-1]
        
        # Call the LiveKit API to get room participants
        api_url = f"{server_url}/rooms/{room_name}/participants"
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = http.get(api_url, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        
        participants = response.json().get("participants", [])
        
        # Check if the identity is in the participants list
        for participant in participants:
            if participant.get("identity") == identity:
                logger.info(f"Validated {identity} is in room {room_name}")
                return True
        
        logger.info(f"{identity} is not in room {room_name}")
        return False
    except requests.RequestException as e:
        logger.error(f"API request failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to validate room membership: {e}")
        raise


def mint_admin_token() -> str:
    """Generate an admin token for LiveKit API access."""
    now = int(time.time())
    payload = {
        "iss": LIVEKIT_API_KEY,
        "nbf": now,
        "exp": now + 60,  # Short-lived token
        "video": {
            "roomList": True,
            "roomCreate": True,
            "roomAdmin": True,
        }
    }
    
    token = jwt.encode(payload, LIVEKIT_API_SECRET, algorithm="HS256")
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token
