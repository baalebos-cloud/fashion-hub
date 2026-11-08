"""LiveKit access tokens for in-app calls.

A token is a JWT signed (HS256) with the project's API secret: iss = API key, sub = the
user's identity, and a `video` grant for exactly one room, microphone only.
Docs: https://docs.livekit.io/frontends/reference/tokens-grants
"""
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings


class AppCallsNotConfigured(Exception):
    pass


def configured() -> bool:
    return bool(settings.LIVEKIT_URL and settings.LIVEKIT_API_KEY and settings.LIVEKIT_API_SECRET)


def join_token(*, room: str, identity: str, name: str, ttl: timedelta) -> str:
    if not configured():
        raise AppCallsNotConfigured("In-app calling isn't set up yet.")
    now = datetime.now(timezone.utc)
    claims = {
        "iss": settings.LIVEKIT_API_KEY, "sub": identity, "name": name,
        "nbf": int((now - timedelta(seconds=10)).timestamp()), "exp": int((now + ttl).timestamp()),
        "video": {"room": room, "roomJoin": True, "canPublish": True, "canSubscribe": True,
                  "canPublishData": False, "canPublishSources": ["microphone"]},
    }
    return jwt.encode(claims, settings.LIVEKIT_API_SECRET, algorithm="HS256")
