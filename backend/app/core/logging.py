"""
Structured logging configuration.

Emits JSON log lines so they can be ingested by any log aggregator
(self-hosted Loki/ELK, journald, etc.) without vendor lock-in. Every log
call can attach a request_id (see middleware.py) for correlation.
"""
import json
import logging
import sys
from datetime import datetime, timezone

from app.core.config import settings

RESERVED_ATTRS = set(logging.LogRecord(None, None, "", 0, "", (), None).__dict__.keys())


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in RESERVED_ATTRS and key not in payload:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

    # Quiet noisy third-party loggers unless we're debugging.
    for noisy in ("uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING if not settings.DEBUG else logging.INFO)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
