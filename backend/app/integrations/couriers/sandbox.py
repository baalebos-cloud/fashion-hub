"""A pretend courier for development, demos and tests. Never used in production.

Quotes are deterministic (base + per km), bookings live in Redis, and status updates arrive as
webhooks signed with HMAC-SHA256 (header X-Sandbox-Signature), exactly like a real courier.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta, timezone

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings
from app.integrations.couriers.base import STATUSES, Booking, CourierAdapter, CourierError, CourierEvent, CourierJob, Quote
from app.services.dispatch_routing import estimate_straight_line_km

MAX_KM = 60


def _redis() -> Redis:
    return Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2, socket_timeout=2)


def sign(body: bytes) -> str:
    return hmac.new((settings.SANDBOX_COURIER_WEBHOOK_SECRET or "").encode(), body, hashlib.sha256).hexdigest()


class SandboxCourier(CourierAdapter):
    name = "sandbox"
    display_name = "Sandbox Courier (test only)"

    def _km(self, job: CourierJob) -> float:
        km = estimate_straight_line_km(job.pickup, job.dropoff)
        if km is None:
            raise CourierError("Pickup or drop-off has no map pin.")
        return km

    def eligible(self, job):
        try:
            km = self._km(job)
        except CourierError as exc:
            return False, str(exc)
        return (km <= MAX_KM, None if km <= MAX_KM else f"farther than {MAX_KM} km")

    def quote(self, job):
        km = self._km(job)
        amount = round((1500 + 120 * km * 1.35) / 50) * 50
        return Quote(courier=self.name, quote_id=f"sbxq_{job.reference}_{int(amount)}", amount_ngn=float(amount),
                     eta_minutes=max(20, round(km * 1.35 / 18 * 60) + 15),
                     expires_at=datetime.now(timezone.utc) + timedelta(minutes=15))

    def book(self, job, quote_id, idempotency_key):
        try:
            redis = _redis()
            existing = redis.get(f"couriers:sandbox:idem:{idempotency_key}")
            if existing:
                return Booking(courier=self.name, external_id=existing.decode(), status="booked",
                               tracking_url=f"https://sandbox-courier.test/track/{existing.decode()}")
            external_id = f"sbx_{uuid.uuid4().hex[:16]}"
            redis.set(f"couriers:sandbox:idem:{idempotency_key}", external_id, ex=86400)
            redis.set(f"couriers:sandbox:job:{external_id}", "booked", ex=7 * 86400)
        except RedisError as exc:
            raise CourierError("Sandbox courier is unavailable.") from exc
        return Booking(courier=self.name, external_id=external_id, status="booked",
                       tracking_url=f"https://sandbox-courier.test/track/{external_id}")

    def cancel(self, external_id):
        try:
            _redis().set(f"couriers:sandbox:job:{external_id}", "cancelled", ex=7 * 86400)
        except RedisError as exc:
            raise CourierError("Sandbox courier is unavailable.") from exc
        return True

    def status(self, external_id):
        try:
            raw = _redis().get(f"couriers:sandbox:job:{external_id}")
        except RedisError as exc:
            raise CourierError("Sandbox courier is unavailable.") from exc
        if raw is None:
            return None
        state = raw.decode()
        return CourierEvent(event_id=f"poll_{external_id}_{state}", external_id=external_id, status=state,
                            occurred_at=datetime.now(timezone.utc))

    # A real courier calls our webhook; the sandbox builds the same signed payload on request.
    def make_webhook(self, external_id: str, status: str, *, proof_url: str | None = None) -> tuple[bytes, dict]:
        if status not in STATUSES:
            raise CourierError("Unknown status.")
        try:
            _redis().set(f"couriers:sandbox:job:{external_id}", status, ex=7 * 86400)
        except RedisError:
            pass
        body = json.dumps({"id": f"evt_{uuid.uuid4().hex[:12]}", "shipment_id": external_id, "status": status,
                           "occurred_at": datetime.now(timezone.utc).isoformat(), "courier": "Test Rider",
                           "proof_url": proof_url}).encode()
        return body, {"x-sandbox-signature": sign(body)}

    def verify_webhook(self, body, headers):
        given = headers.get("x-sandbox-signature", "")
        return bool(settings.SANDBOX_COURIER_WEBHOOK_SECRET) and hmac.compare_digest(given, sign(body))

    def parse_webhook(self, body):
        data = json.loads(body)
        return CourierEvent(event_id=str(data["id"]), external_id=str(data["shipment_id"]), status=str(data["status"]),
                            occurred_at=datetime.fromisoformat(data["occurred_at"]), courier_name=data.get("courier"),
                            proof_of_delivery_url=data.get("proof_url"))
