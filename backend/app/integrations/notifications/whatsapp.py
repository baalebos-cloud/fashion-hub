"""
WhatsApp sending abstraction. Two mainstream ways to send WhatsApp
messages programmatically as of this writing:

  - Meta's own WhatsApp Cloud API (graph.facebook.com) -- free tier
    available, requires a verified WhatsApp Business phone number.
  - Twilio's WhatsApp API -- wraps the same underlying WhatsApp Business
    Platform with Twilio's simpler auth/SDK, at a small per-message markup.

Either works from this same interface; WHATSAPP_PROVIDER picks which.
Selected because the product spec calls WhatsApp "the easiest way to
notify" vendors and tailors/designers of each other's order activity --
this is a genuine, separate channel from SMS/push (see
core/constants.py::NotificationChannel.WHATSAPP), not SMS-with-a-different-
label, since WhatsApp requires pre-approved message templates for
business-initiated conversations.
"""
import httpx

from app.core.config import settings
from app.core.exceptions import ExternalProviderError

GRAPH_API_BASE = "https://graph.facebook.com/v19.0"


def send_whatsapp_message(*, to_phone: str, template_name: str, template_params: list[str] | None = None) -> None:
    """
    `to_phone` must be in E.164 format (e.g. +2348012345678).
    `template_name` must be a pre-approved WhatsApp message template --
    free-form text only works within a 24h customer-initiated window,
    which doesn't apply to platform-initiated order notifications.
    """
    if not settings.WHATSAPP_PROVIDER:
        raise ExternalProviderError("No WHATSAPP_PROVIDER configured.")

    if settings.WHATSAPP_PROVIDER == "meta_cloud_api":
        _send_via_meta_cloud_api(to_phone, template_name, template_params or [])
    elif settings.WHATSAPP_PROVIDER == "twilio":
        _send_via_twilio(to_phone, template_name, template_params or [])
    else:
        raise ExternalProviderError(f"Unsupported WHATSAPP_PROVIDER '{settings.WHATSAPP_PROVIDER}'")


def _send_via_meta_cloud_api(to_phone: str, template_name: str, params: list[str]) -> None:
    try:
        response = httpx.post(
            f"{GRAPH_API_BASE}/{settings.WHATSAPP_FROM_NUMBER}/messages",
            headers={"Authorization": f"Bearer {settings.WHATSAPP_API_KEY}"},
            json={
                "messaging_product": "whatsapp",
                "to": to_phone.lstrip("+"),
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": "en_US"},
                    "components": [{"type": "body", "parameters": [{"type": "text", "text": p} for p in params]}] if params else [],
                },
            },
            timeout=10.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ExternalProviderError(f"WhatsApp (Meta Cloud API) send failed: {exc}") from exc


def _send_via_twilio(to_phone: str, template_name: str, params: list[str]) -> None:
    # Twilio's WhatsApp templates are referenced by Content SID, not name;
    # `template_name` here is expected to already be that SID when using
    # this provider (map friendly names to SIDs in a small constant table
    # once real templates are approved).
    try:
        response = httpx.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{settings.WHATSAPP_FROM_NUMBER}/Messages.json",
            auth=(settings.WHATSAPP_FROM_NUMBER or "", settings.WHATSAPP_API_KEY or ""),
            data={
                "To": f"whatsapp:{to_phone}",
                "From": f"whatsapp:{settings.WHATSAPP_FROM_NUMBER}",
                "ContentSid": template_name,
                "ContentVariables": str({str(i + 1): p for i, p in enumerate(params)}),
            },
            timeout=10.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ExternalProviderError(f"WhatsApp (Twilio) send failed: {exc}") from exc
