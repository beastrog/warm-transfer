import os
from typing import Optional
from livekit import AccessToken, VideoGrants
from dotenv import load_dotenv

# Load env from a local .env if present
load_dotenv()

LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")


def mint_access_token(*, room_name: str, identity: str, role: Optional[str] = None, ttl_seconds: int = 3600) -> str:
    if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
        raise RuntimeError("LIVEKIT_API_KEY and LIVEKIT_API_SECRET must be set")

    token = AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    grants = VideoGrants(room=room_name, room_join=True)
    token.identity = identity
    token.ttl = ttl_seconds
    token.grants = grants
    return token.to_jwt()
