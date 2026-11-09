"""Prembly "NIN with face": does this face match the photo on the government NIN record?

Used twice per identity submission: the live selfie taken during submission, and the profile photo
customers will see. Both must match the NIN record photo, so someone can't verify with another
person's NIN, or show another person's face on their profile.

Images are sent to Prembly only for this comparison. Nothing from the reply except the match result
and confidence is kept; images, NINs and provider payloads are never logged.
"""
from __future__ import annotations

import base64
import logging
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.core.exceptions import ExternalProviderError

logger = logging.getLogger(__name__)


@dataclass
class FaceMatch:
    matched: bool
    confidence: float | None  # 0–100, as Prembly reports it


def compare_face_with_nin(nin_number: str, image: bytes, *, http_post=None) -> FaceMatch:
    """Raises ExternalProviderError when the comparison couldn't be made (the caller then sends the
    submission to an admin); returns matched=False only when Prembly compared and found no match."""
    api_key = settings.PREMBLY_API_KEY or settings.NIN_API_KEY
    if not api_key:
        raise ExternalProviderError("Face matching is not configured.")
    if not image:
        raise ExternalProviderError("No face photo to compare.")
    post = http_post or httpx.post
    try:
        response = post(settings.PREMBLY_NIN_FACE_URL,
                        headers={"x-api-key": api_key, "accept": "application/json"},
                        json={"number": nin_number, "image": base64.b64encode(image).decode(),
                              "face_confidence_threshold": settings.NIN_FACE_THRESHOLD},
                        timeout=25.0)
    except httpx.HTTPError:
        logger.warning("nin_face_request_failed provider=prembly")
        raise ExternalProviderError("Face matching is temporarily unavailable.") from None
    if response.status_code != 200:
        logger.warning("nin_face_http_error provider=prembly status=%d", response.status_code)
        raise ExternalProviderError(f"Face matching failed (HTTP {response.status_code}).")
    try:
        payload = response.json()
    except ValueError:
        raise ExternalProviderError("Face matching returned an invalid reply.") from None
    face = payload.get("face_data") if isinstance(payload, dict) else None
    if not isinstance(face, dict):
        # No comparison happened (e.g. NIN not found, or the product isn't enabled on the account).
        code = str((payload or {}).get("response_code") or "")[:8] if isinstance(payload, dict) else ""
        logger.warning("nin_face_no_result provider=prembly code=%s", code or "-")
        raise ExternalProviderError("Face matching returned no result.")
    confidence = face.get("confidence")
    try:
        confidence = float(confidence) if confidence is not None else None
    except (TypeError, ValueError):
        confidence = None
    if confidence is not None and confidence <= 1:
        confidence *= 100  # some replies give 0–1
    status = face.get("status")
    matched = (status is True or str(status).lower() in {"true", "match", "matched", "success"}) and (
        confidence is None or confidence >= settings.NIN_FACE_THRESHOLD)
    return FaceMatch(matched=matched, confidence=round(confidence, 1) if confidence is not None else None)
