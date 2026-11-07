"""The contract every courier adapter implements. Business logic only ever sees these types."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from app.core.exceptions import ExternalProviderError

# Courier statuses are normalised to these; anything else is ignored with a log line.
STATUSES = ("booked", "courier_assigned", "picked_up", "in_transit", "delivered", "failed", "cancelled")
FINAL = {"delivered", "failed", "cancelled"}
RANK = {s: i for i, s in enumerate(STATUSES[:5])}  # forward-only progress; failed/cancelled handled apart


@dataclass(frozen=True)
class CourierJob:
    reference: str               # our delivery request id
    pickup: dict                 # {"latitude", "longitude", "address", "contact_name"}
    dropoff: dict
    package_description: str
    package_value_ngn: float | None = None


@dataclass(frozen=True)
class Quote:
    courier: str
    quote_id: str
    amount_ngn: float
    eta_minutes: int | None
    expires_at: datetime | None
    service_level: str = "standard"


@dataclass(frozen=True)
class Booking:
    courier: str
    external_id: str
    status: str
    tracking_url: str | None = None


@dataclass(frozen=True)
class CourierEvent:
    event_id: str                # the courier's id for this event: used to drop duplicates
    external_id: str
    status: str
    occurred_at: datetime
    courier_name: str | None = None
    proof_of_delivery_url: str | None = None
    note: str | None = None
    extra: dict = field(default_factory=dict)


class CourierError(ExternalProviderError):
    """The courier's API failed or refused. No local state is changed."""


class CourierAdapter(ABC):
    name: str = ""
    display_name: str = ""

    @abstractmethod
    def eligible(self, job: CourierJob) -> tuple[bool, str | None]:
        """Can this courier take the job at all (area, size)? (ok, reason if not)."""

    @abstractmethod
    def quote(self, job: CourierJob) -> Quote: ...

    @abstractmethod
    def book(self, job: CourierJob, quote_id: str, idempotency_key: str) -> Booking: ...

    @abstractmethod
    def cancel(self, external_id: str) -> bool: ...

    @abstractmethod
    def status(self, external_id: str) -> CourierEvent | None:
        """Latest status straight from the courier, used by reconciliation for missed webhooks."""

    @abstractmethod
    def verify_webhook(self, body: bytes, headers: dict) -> bool: ...

    @abstractmethod
    def parse_webhook(self, body: bytes) -> CourierEvent: ...
