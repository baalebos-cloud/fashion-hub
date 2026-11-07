"""
Cross-cutting HTTP middleware: request ID propagation, structured access
logging, and basic latency measurement. Rate limiting is wired in main.py
via slowapi (keyed off client IP or authenticated user).
"""
import time
import uuid
import re

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.logging import get_logger

logger = get_logger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    - Assigns/propagates a request ID for correlating logs across
      API -> service -> background job -> provider webhook.
    - Logs method, path, status code, and latency for every request.
    """

    async def dispatch(self, request: Request, call_next):
        supplied_id = request.headers.get(REQUEST_ID_HEADER, "")
        request_id = supplied_id if re.fullmatch(r"[A-Za-z0-9._-]{1,64}", supplied_id) else str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.monotonic()

        response = await call_next(request)

        duration_ms = round((time.monotonic() - start) * 1000, 2)
        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        logger.info(
            "http_request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response


# Changes worth an audit trail. Reads are not logged; noisy machine traffic is skipped.
_LOGGED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_SKIP_SUFFIXES = ("/position", "/position/start")
# Auth endpoints log their own, richer entries (sign-in success/failure and who).
_SKIP_PREFIXES = ("/api/v1/auth/", "/health", "/api/v1/payments/webhook", "/api/v1/webhooks", "/api/v1/calls/voice",
                 # Shopping-activity batches: high volume, and recorded without IP by design.
                 "/api/v1/interactions/events")


class ActivityLogMiddleware(BaseHTTPMiddleware):
    """Records every change made through the API: who, which endpoint, outcome, IP, device."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        path = request.url.path
        if (request.method in _LOGGED_METHODS and path.startswith("/api/")
                and not path.startswith(_SKIP_PREFIXES) and not path.endswith(_SKIP_SUFFIXES)):
            from starlette.concurrency import run_in_threadpool
            from app.services.activity_service import record
            identity = _token_identity(request)
            # Full path with ids swapped for {placeholders}, so entries group by endpoint.
            template = path
            for name, value in (request.scope.get("path_params") or {}).items():
                template = template.replace("/" + str(value), "/{" + name + "}")
            await run_in_threadpool(record, request, "request", user_id=identity[0], role=identity[1],
                                    status_code=response.status_code, path=template)
        return response


def _token_identity(request: Request) -> tuple:
    """User id and role from the bearer token, without a database round trip. An invalid token
    yields (None, None): the request was anonymous or rejected anyway."""
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        return None, None
    try:
        import uuid as _uuid
        from app.core.security import decode_token
        payload = decode_token(header[7:].strip(), expected_type="access")
        return _uuid.UUID(payload["sub"]), payload.get("role")
    except Exception:
        return None, None
