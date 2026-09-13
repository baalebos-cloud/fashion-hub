"""
Application-level exception hierarchy and their FastAPI handlers.

Services and repositories raise these domain exceptions instead of HTTPException
directly, so business logic stays framework-agnostic and testable without
spinning up FastAPI. Route layer (or the global handlers registered in
main.py) translates them into consistent JSON error responses.
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base class for all domain/business errors."""
    status_code: int = status.HTTP_400_BAD_REQUEST
    error_code: str = "app_error"

    def __init__(self, message: str, *, error_code: str = None, status_code: int = None):
        super().__init__(message)
        self.message = message
        if error_code:
            self.error_code = error_code
        if status_code:
            self.status_code = status_code


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "not_found"


class ValidationAppError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "validation_error"


class ConflictError(AppError):
    """E.g. product sold out mid-checkout, duplicate order submission."""
    status_code = status.HTTP_409_CONFLICT
    error_code = "conflict"


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "forbidden"


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "unauthorized"


class InvalidStateTransitionError(AppError):
    """E.g. attempting to mark an order RECEIVED before it is DELIVERED."""
    status_code = status.HTTP_409_CONFLICT
    error_code = "invalid_state_transition"


class PaymentError(AppError):
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    error_code = "payment_error"


class ExternalProviderError(AppError):
    """Wraps failures from payment/maps/delivery/KYC/AI providers so callers
    never leak provider-specific exception types up the stack."""
    status_code = status.HTTP_502_BAD_GATEWAY
    error_code = "external_provider_error"


class RateLimitedError(AppError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_code = "rate_limited"


def _error_body(exc: AppError, request: Request) -> dict:
    return {
        "error": {
            "code": exc.error_code,
            "message": exc.message,
            "request_id": getattr(request.state, "request_id", None),
        }
    }


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=_error_body(exc, request))


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    from app.core.logging import get_logger
    logger = get_logger(__name__)
    logger.exception("unhandled_exception", extra={"request_id": getattr(request.state, "request_id", None)})
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "internal_server_error",
                "message": "An unexpected error occurred.",
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


def register_exception_handlers(app):
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
