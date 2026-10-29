"""Prembly NIN Basic verification (current public API contract).

Only verified provider data can populate identity fields. Raw NINs, tokens,
provider payloads and photos are never logged.
"""
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

import httpx

from app.core.config import settings
from app.core.exceptions import ExternalProviderError, NotFoundError
from app.integrations.kyc.nin_provider import NINVerificationProvider, NINVerificationResult

PREMBLY_BASE_URL = "https://api.prembly.com/verification/vnin-basic"


class PremblyNINProvider(NINVerificationProvider):
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.NIN_API_KEY

    def verify(self, nin_number: str) -> NINVerificationResult:
        if not self.api_key:
            raise ExternalProviderError("NIN verification is not configured. Contact support.")
        if not nin_number.isascii() or len(nin_number) != 11 or not nin_number.isdecimal():
            raise NotFoundError("Enter a valid 11-digit NIN.")
        try:
            response = httpx.post(
                PREMBLY_BASE_URL,
                headers={"x-api-key": self.api_key, "accept": "application/json"},
                json={"number": nin_number},
                timeout=15.0,
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            logger.warning("nin_provider_http_error provider=prembly status=%d", code)
            if code in (401, 403):
                raise ExternalProviderError("NIN verification access rejected by provider. Contact support to check API credentials and product access.") from exc
            if code == 429:
                raise ExternalProviderError("NIN verification is rate-limited. Try again later.") from exc
            raise ExternalProviderError("NIN verification provider is temporarily unavailable.") from exc
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("nin_provider_request_failed provider=prembly type=%s", type(exc).__name__)
            raise ExternalProviderError("NIN verification provider is temporarily unavailable.") from exc

        if not isinstance(payload, dict):
            raise ExternalProviderError("NIN verification response is invalid.")
        if payload.get("status") is not True or payload.get("response_code") != "00":
            raise NotFoundError("NIN could not be verified. Check your details or contact support.")
        record = payload.get("data") or payload.get("nin_data")
        if not isinstance(record, dict):
            raise ExternalProviderError("NIN provider did not return identity details.")
        full_name = " ".join(str(record.get(k) or "").strip() for k in
                             ("firstname", "middlename", "surname")).strip()
        date_raw = record.get("birthdate")
        try:
            dob = datetime.strptime(date_raw, "%d-%m-%Y").date()
        except (TypeError, ValueError) as exc:
            raise ExternalProviderError("NIN provider returned an unsupported date format.") from exc
        if not full_name or not record.get("firstname") or not record.get("surname"):
            raise ExternalProviderError("NIN provider returned incomplete identity details.")
        return NINVerificationResult(
            nin=nin_number,
            full_name=full_name,
            date_of_birth=dob,
            gender=str(record.get("gender") or "").upper(),
            photo_base64=record.get("photo"),
        )
