"""Who is on the other end of a request: IP, browser/device description and device ID.

Behind Railway's proxy the socket address is the proxy, so with TRUST_PROXY_HEADERS on we
read X-Real-IP, else the last X-Forwarded-For hop (the one the proxy added, which a client
cannot forge). Browsers never expose a device's MAC address to websites, so the device ID is
a random value the web app keeps in the browser and sends as X-Device-Id.
"""
import ipaddress
import re

from starlette.requests import Request

from app.core.config import settings

DEVICE_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")


def _valid_ip(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return str(ipaddress.ip_address(value.strip()))
    except ValueError:
        return None


def client_ip(request: Request) -> str | None:
    if settings.TRUST_PROXY_HEADERS:
        real = _valid_ip(request.headers.get("x-real-ip"))
        if real:
            return real
        forwarded = [hop for hop in request.headers.get("x-forwarded-for", "").split(",") if hop.strip()]
        if forwarded:
            last = _valid_ip(forwarded[-1])
            if last:
                return last
    return _valid_ip(request.client.host) if request.client else None


def device_id(request: Request) -> str | None:
    value = request.headers.get("x-device-id", "")
    return value if DEVICE_ID.match(value) else None


def user_agent(request: Request) -> str | None:
    value = request.headers.get("user-agent")
    return value[:300] if value else None
