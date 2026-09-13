"""Handlers that translate domain events into notification dispatch (thin
wrapper delegating to notification_service via a background task)."""
from app.events.publisher import subscribe


def _on_review_created(**payload):
    # E.g. notify the professional that they received a new review.
    pass


def register() -> None:
    subscribe("review.created", _on_review_created)
