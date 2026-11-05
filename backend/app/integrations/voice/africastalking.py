"""Africa's Talking Voice: ring a user, then bridge them via XML from our webhook.

Call flow (both parties only ever see Tailora's virtual number):
1. place_call(caller_phone) -> AT rings the caller from AT_VOICE_NUMBER.
2. Caller answers -> AT POSTs our voice webhook -> we answer with <Dial> to the callee.
"""
from __future__ import annotations

import uuid
from xml.sax.saxutils import escape, quoteattr

import httpx

from app.core.config import settings
from app.core.exceptions import ExternalProviderError
from app.core.logging import get_logger

logger = get_logger(__name__)


class VoiceNotConfigured(RuntimeError):
    pass


def _voice_base_url() -> str:
    return ("https://voice.africastalking.com" if settings.AT_ENVIRONMENT == "production"
            else "https://voice.sandbox.africastalking.com")


def place_call(*, to_phone: str, client_request_id: str, http_post=None) -> str:
    """Ring ``to_phone`` from Tailora's number. Returns the provider session id."""
    provider = (settings.VOICE_PROVIDER or "").lower()
    if provider == "sandbox":
        return f"sandbox-{uuid.uuid4().hex}"
    if provider != "africastalking" or not (settings.AT_USERNAME and settings.AT_API_KEY and settings.AT_VOICE_NUMBER):
        raise VoiceNotConfigured("In-app calling isn't set up yet.")
    post = http_post or httpx.post
    try:
        response = post(
            f"{_voice_base_url()}/call",
            headers={"apiKey": settings.AT_API_KEY, "Accept": "application/json"},
            data={"username": settings.AT_USERNAME, "from": settings.AT_VOICE_NUMBER,
                  "to": to_phone, "clientRequestId": client_request_id},
            timeout=15.0,
        )
    except httpx.RequestError:
        logger.warning("tailora_voice_transport_failure")
        raise ExternalProviderError("Calling is temporarily unavailable. Please try again.") from None
    if response.status_code not in (200, 201):
        logger.warning("tailora_voice_api_failure", extra={"status": response.status_code})
        raise ExternalProviderError("Calling is temporarily unavailable. Please try again.")
    try:
        entry = response.json()["entries"][0]
        if str(entry.get("status", "")).lower() not in {"queued", "success"}:
            raise ValueError(entry.get("status"))
        return str(entry["sessionId"])
    except (ValueError, KeyError, IndexError, TypeError):
        logger.warning("tailora_voice_call_rejected")
        raise ExternalProviderError("The call could not be placed. Check your phone number in Settings.") from None


def xml_response(*parts: str) -> str:
    return '<?xml version="1.0" encoding="UTF-8"?><Response>' + "".join(parts) + "</Response>"


def say(text: str) -> str:
    return f"<Say>{escape(text)}</Say>"


def dial(phone: str) -> str:
    attrs = {
        "phoneNumbers": phone, "record": "false", "sequential": "true",
        "maxDuration": str(settings.VOICE_MAX_CALL_SECONDS),
    }
    if settings.AT_VOICE_NUMBER:
        attrs["callerId"] = settings.AT_VOICE_NUMBER
    return "<Dial " + " ".join(f"{k}={quoteattr(v)}" for k, v in attrs.items()) + "/>"
