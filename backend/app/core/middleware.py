"""
Cross-cutting HTTP middleware: request ID propagation, structured access
logging, and basic latency measurement. Rate limiting is wired in main.py
via slowapi (keyed off client IP or authenticated user).
"""
import time
import uuid

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
        request_id = request.headers.get(REQUEST_ID_HEADER, str(uuid.uuid4()))
        request.state.request_id = request_id
        start = time.monotonic()

        response = await call_next(request)

        duration_ms = round((time.monotonic() - start) * 1000, 2)
        response.headers[REQUEST_ID_HEADER] = request_id
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
