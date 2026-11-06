"""RFC 6238 time-based one-time codes (what Google Authenticator, Authy and 1Password use).

Six digits, 30-second steps, SHA-1, accepting one step of clock drift either way. The caller
stores the last accepted step so a code can't be replayed.
"""
import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

STEP_SECONDS = 30
DIGITS = 6


def new_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _code(secret: str, counter: int) -> str:
    key = base64.b32decode(secret + "=" * (-len(secret) % 8), casefold=True)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return f"{value % 10 ** DIGITS:0{DIGITS}d}"


def current_counter(now: float | None = None) -> int:
    return int((time.time() if now is None else now) // STEP_SECONDS)


def code_for(secret: str, now: float | None = None) -> str:
    return _code(secret, current_counter(now))


def verify(secret: str, submitted: str, *, last_counter: int | None, now: float | None = None) -> int | None:
    """Return the matched time step, or None. Steps at or before last_counter are refused."""
    if not submitted or len(submitted) != DIGITS or not submitted.isascii() or not submitted.isdecimal():
        return None
    base = current_counter(now)
    for counter in (base - 1, base, base + 1):
        if last_counter is not None and counter <= last_counter:
            continue
        if hmac.compare_digest(_code(secret, counter), submitted):
            return counter
    return None


def provisioning_uri(secret: str, account: str, issuer: str) -> str:
    label = quote(f"{issuer}:{account}")
    return f"otpauth://totp/{label}?secret={secret}&issuer={quote(issuer)}&algorithm=SHA1&digits={DIGITS}&period={STEP_SECONDS}"
