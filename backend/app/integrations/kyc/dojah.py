"""Dojah NIN lookup (Basic tier): GET /api/v1/kyc/nin?nin=..., headers AppId + Authorization (secret key).

Docs: https://docs.dojah.io/api-reference/individual-verification/nigeria/lookup-nin
Raw NINs, keys, provider payloads and photos are never logged.
"""
import logging
from datetime import datetime

import httpx

from app.core.config import settings
from app.core.exceptions import ExternalProviderError, NotFoundError
from app.integrations.kyc.nin_provider import NINVerificationProvider, NINVerificationResult

logger = logging.getLogger(__name__)


class DojahNINProvider(NINVerificationProvider):
    def __init__(self, secret_key: str | None = None, app_id: str | None = None, base_url: str | None = None):
        self.secret_key = secret_key or settings.NIN_API_KEY
        self.app_id = app_id or settings.DOJAH_APP_ID
        self.base_url = (base_url or settings.DOJAH_BASE_URL).rstrip("/")

    def verify(self, nin_number: str) -> NINVerificationResult:
        if not self.secret_key or not self.app_id:
            raise ExternalProviderError("NIN verification is not configured. Contact support.")
        if not nin_number.isascii() or len(nin_number) != 11 or not nin_number.isdecimal():
            raise NotFoundError("Enter a valid 11-digit NIN.")
        try:
            response = httpx.get(f"{self.base_url}/api/v1/kyc/nin", params={"nin": nin_number},
                                 headers={"AppId": self.app_id, "Authorization": self.secret_key, "accept": "application/json"},
                                 timeout=15.0)
        except httpx.HTTPError as exc:
            logger.warning("nin_provider_request_failed provider=dojah type=%s", type(exc).__name__)
            raise ExternalProviderError("NIN verification provider is temporarily unavailable.") from exc
        code = response.status_code
        if code == 404:
            raise NotFoundError("NIN could not be verified. Check your details or contact support.")
        if code != 200:
            logger.warning("nin_provider_http_error provider=dojah status=%d", code)
            if code in (401, 403):
                raise ExternalProviderError("NIN verification access rejected by provider. Contact support to check API credentials.")
            if code == 402:
                raise ExternalProviderError("NIN verification is paused (provider balance). Your details will be reviewed by hand.")
            if code == 429:
                raise ExternalProviderError("NIN verification is rate-limited. Try again later.")
            raise ExternalProviderError("NIN verification provider is temporarily unavailable.")
        try:
            payload = response.json()
        except ValueError as exc:
            raise ExternalProviderError("NIN verification response is invalid.") from exc
        record = payload.get("entity") if isinstance(payload, dict) else None
        if not isinstance(record, dict) or not record:
            raise NotFoundError("NIN could not be verified. Check your details or contact support.")
        first, middle, last = (str(record.get(k) or "").strip() for k in ("first_name", "middle_name", "last_name"))
        if not first or not last:
            raise ExternalProviderError("NIN provider returned incomplete identity details.")
        dob_raw = str(record.get("date_of_birth") or "")
        dob = None
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
            try:
                dob = datetime.strptime(dob_raw, fmt).date()
                break
            except ValueError:
                continue
        if dob is None:
            raise ExternalProviderError("NIN provider returned an unsupported date format.")
        return NINVerificationResult(nin=nin_number, full_name=" ".join(p for p in (first, middle, last) if p),
                                     date_of_birth=dob, gender=str(record.get("gender") or "").upper(),
                                     photo_base64=record.get("photo"))
