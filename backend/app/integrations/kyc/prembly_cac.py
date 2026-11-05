"""Prembly CAC (Corporate Affairs Commission) lookup for Nigerian business KYB.

Returns only the registry's company name and status. Raw provider payloads,
keys and directors' details are never logged or stored.

Prembly has published more than one URL for this product, so the endpoint
is configurable (PREMBLY_CAC_URL). Any provider failure is reported as
ExternalProviderError, which the KYB flow turns into manual admin review.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.core.exceptions import ExternalProviderError, NotFoundError

logger = logging.getLogger(__name__)


@dataclass
class CACResult:
    company_name: str
    registration_status: str | None


def lookup_cac(rc_number: str, company_type: str, http_post=None) -> CACResult:
    if (settings.KYB_PROVIDER or "manual").lower() != "prembly":
        raise ExternalProviderError("Automatic business lookup is not enabled.")
    api_key = settings.PREMBLY_API_KEY or settings.NIN_API_KEY
    if not api_key:
        raise ExternalProviderError("Business lookup is not configured.")
    post = http_post or httpx.post
    try:
        response = post(settings.PREMBLY_CAC_URL,
                        headers={"x-api-key": api_key, "accept": "application/json"},
                        json={"rc_number": rc_number, "company_type": company_type}, timeout=15.0)
    except httpx.HTTPError:
        logger.warning("kyb_provider_request_failed provider=prembly")
        raise ExternalProviderError("Business lookup is temporarily unavailable.") from None
    if response.status_code == 404:
        raise NotFoundError("We couldn't find that registration number with CAC.")
    if response.status_code != 200:
        logger.warning("kyb_provider_http_error provider=prembly status=%d", response.status_code)
        raise ExternalProviderError("Business lookup is temporarily unavailable.")
    try:
        payload = response.json()
    except ValueError:
        raise ExternalProviderError("Business lookup returned an invalid response.") from None
    if not isinstance(payload, dict):
        raise ExternalProviderError("Business lookup returned an invalid response.")
    if payload.get("status") is not True or str(payload.get("response_code", "00")) != "00":
        # Prembly signals "no record" this way; a typo is the most likely cause.
        raise NotFoundError("We couldn't find that registration number with CAC.")
    record = payload.get("data")
    if isinstance(record, list):
        record = record[0] if record else None
    if not isinstance(record, dict):
        raise ExternalProviderError("Business lookup returned no company details.")
    name = next((str(record[k]).strip() for k in ("company_name", "companyName", "approvedName", "name")
                 if record.get(k)), "")
    if not name:
        raise ExternalProviderError("Business lookup returned no company name.")
    status = next((str(record[k]) for k in ("status", "companyStatus", "company_status") if record.get(k)), None)
    return CACResult(company_name=name[:255], registration_status=status)
