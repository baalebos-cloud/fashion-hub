"""Push to the iPhone and Android apps: Apple (APNs, HTTP/2 + ES256 token) and Firebase (FCM HTTP v1).

Each sender returns "sent", "invalid" (the phone's token is dead: delete it) or "failed"
(try again another time). Tokens, keys and message bodies are never logged.
Both are off until their settings are present.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from contextlib import nullcontext
from dataclasses import dataclass, field

import httpx
import jwt

from app.core.config import settings

logger = logging.getLogger(__name__)

APNS_HOSTS = {True: "https://api.sandbox.push.apple.com", False: "https://api.push.apple.com"}
FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"


@dataclass
class PushMessage:
    title: str
    body: str
    data: dict = field(default_factory=dict)
    collapse_id: str | None = None  # a later message with the same id replaces this one
    ttl_seconds: int = 60
    urgent: bool = False  # ring: time-sensitive on iOS, the "calls" channel on Android


def apns_configured() -> bool:
    return bool(settings.APNS_KEY_ID and settings.APNS_TEAM_ID and settings.APNS_PRIVATE_KEY)


def fcm_configured() -> bool:
    return bool(settings.FCM_PROJECT_ID and settings.FCM_SERVICE_ACCOUNT_JSON)


# ---- Apple ---------------------------------------------------------------------------
_apns_token: tuple[str, float] | None = None
_lock = threading.Lock()


def _apns_auth() -> str:
    """Provider token, reused for 50 minutes (Apple accepts up to 60)."""
    global _apns_token
    with _lock:
        if _apns_token and time.time() - _apns_token[1] < 50 * 60:
            return _apns_token[0]
        key = (settings.APNS_PRIVATE_KEY or "").replace("\\n", "\n")
        token = jwt.encode({"iss": settings.APNS_TEAM_ID, "iat": int(time.time())}, key,
                           algorithm="ES256", headers={"kid": settings.APNS_KEY_ID})
        _apns_token = (token, time.time())
        return token


def send_apns(device_token: str, message: PushMessage, *, client: httpx.Client | None = None) -> str:
    if not apns_configured():
        return "failed"
    aps: dict = {"alert": {"title": message.title, "body": message.body}, "sound": "default"}
    if message.urgent:
        aps["interruption-level"] = "time-sensitive"
        aps["category"] = "INCOMING_CALL"
    headers = {
        "authorization": f"bearer {_apns_auth()}",
        "apns-topic": settings.APNS_BUNDLE_ID,
        "apns-push-type": "alert",
        "apns-priority": "10" if message.urgent else "5",
        "apns-expiration": str(int(time.time()) + message.ttl_seconds),
    }
    if message.collapse_id:
        headers["apns-collapse-id"] = message.collapse_id[:64]
    url = f"{APNS_HOSTS[settings.APNS_USE_SANDBOX]}/3/device/{device_token}"
    try:
        with (nullcontext(client) if client else httpx.Client(http2=True, timeout=5.0)) as http:
            response = http.post(url, headers=headers, content=json.dumps({"aps": aps, **message.data}))
    except httpx.HTTPError as exc:
        logger.warning("push_failed provider=apns type=%s", type(exc).__name__)
        return "failed"
    if response.status_code == 200:
        return "sent"
    reason = ""
    try:
        reason = response.json().get("reason", "")
    except ValueError:
        pass
    logger.warning("push_failed provider=apns status=%d reason=%s", response.status_code, reason)
    if response.status_code == 410 or reason in {"BadDeviceToken", "Unregistered", "DeviceTokenNotForTopic"}:
        return "invalid"
    return "failed"


# ---- Firebase ------------------------------------------------------------------------
_fcm_credentials = None


def _fcm_access_token() -> str:
    global _fcm_credentials
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account
    with _lock:
        if _fcm_credentials is None:
            info = json.loads(settings.FCM_SERVICE_ACCOUNT_JSON or "{}")
            _fcm_credentials = service_account.Credentials.from_service_account_info(info, scopes=[FCM_SCOPE])
        if not _fcm_credentials.valid:
            _fcm_credentials.refresh(Request())
        return _fcm_credentials.token


def send_fcm(device_token: str, message: PushMessage, *, client: httpx.Client | None = None) -> str:
    if not fcm_configured():
        return "failed"
    android: dict = {
        "priority": "HIGH" if message.urgent else "NORMAL",
        "ttl": f"{message.ttl_seconds}s",
        "notification": {"title": message.title, "body": message.body},
    }
    if message.collapse_id:
        android["collapse_key"] = message.collapse_id[:64]
        android["notification"]["tag"] = message.collapse_id[:64]
    if message.urgent:
        android["notification"].update(channel_id="calls", sound="ringtone", notification_priority="PRIORITY_MAX",
                                       visibility="PUBLIC", default_vibrate_timings=True)
    body = {"message": {"token": device_token, "android": android,
                        "data": {k: str(v) for k, v in message.data.items()}}}
    url = f"https://fcm.googleapis.com/v1/projects/{settings.FCM_PROJECT_ID}/messages:send"
    try:
        with (nullcontext(client) if client else httpx.Client(timeout=5.0)) as http:
            response = http.post(url, json=body, headers={"authorization": f"Bearer {_fcm_access_token()}"})
    except Exception as exc:  # network or credential errors
        logger.warning("push_failed provider=fcm type=%s", type(exc).__name__)
        return "failed"
    if response.status_code == 200:
        return "sent"
    status = ""
    try:
        status = response.json().get("error", {}).get("status", "")
    except ValueError:
        pass
    logger.warning("push_failed provider=fcm status=%d error=%s", response.status_code, status)
    if response.status_code == 404 or status in {"UNREGISTERED", "NOT_FOUND"}:
        return "invalid"
    return "failed"


def send(platform: str, device_token: str, message: PushMessage) -> str:
    if platform == "ios":
        return send_apns(device_token, message)
    if platform == "android":
        return send_fcm(device_token, message)
    return "failed"
