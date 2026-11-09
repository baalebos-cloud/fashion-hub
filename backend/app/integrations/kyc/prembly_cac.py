"""Prembly CAC (Corporate Affairs Commission) lookup for Nigerian business KYB.

Returns the registry's company name and status, and the people listed on the company
(directors, proprietors, shareholders) for the automatic-approval check. The people are
used in memory only: raw provider payloads, keys and directors' details are never logged
or stored.

Prembly has published more than one URL for this product, so the endpoint
is configurable (PREMBLY_CAC_URL). Any provider failure is reported as
ExternalProviderError, which the KYB flow turns into manual admin review.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime

import httpx

from app.core.config import settings
from app.core.exceptions import ExternalProviderError, NotFoundError

logger = logging.getLogger(__name__)


@dataclass
class CACPerson:
    full_name: str
    date_of_birth: date | None
    role: str | None  # e.g. DIRECTOR, PROPRIETOR, SHAREHOLDER, SECRETARY (as the registry names it)
    active: bool


@dataclass
class CACResult:
    company_name: str
    registration_status: str | None
    people: list[CACPerson] = field(default_factory=list)


def _date(value) -> date | None:
    text = str(value or "").strip()[:10]
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _people(record: dict) -> list[CACPerson]:
    raw = record.get("directors") or record.get("affiliates") or []
    people = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict) or item.get("isCorporate") is True:
            continue  # a company holding shares is not a person who can own this account
        name = " ".join(str(item.get(k) or "").strip() for k in ("firstname", "otherName", "surname")).strip()
        if not name:
            name = str(item.get("name") or item.get("fullName") or "").strip()
        if not name:
            continue
        kind = item.get("affiliateTypeFk")
        role = (kind.get("name") if isinstance(kind, dict) else None) or item.get("affiliateType") or item.get("role")
        status = str(item.get("status") or "").strip().upper()
        people.append(CACPerson(full_name=name[:255], date_of_birth=_date(item.get("dateOfBirth")),
                                role=str(role).strip().upper()[:64] if role else None,
                                active=status in {"", "ACTIVE"}))
    return people


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
    # An HTTP 404 means the endpoint URL is wrong, not that the company is missing:
    # Prembly reports "no record" as response_code 01 in a normal 200 reply. Never
    # turn a misconfiguration into "your registration number doesn't exist".
    if response.status_code != 200:
        logger.warning("kyb_provider_http_error provider=prembly status=%d", response.status_code)
        raise ExternalProviderError("Business lookup is temporarily unavailable.")
    try:
        payload = response.json()
    except ValueError:
        raise ExternalProviderError("Business lookup returned an invalid response.") from None
    if not isinstance(payload, dict):
        raise ExternalProviderError("Business lookup returned an invalid response.")
    # Prembly response codes: 00 success, 01 not found, 02 service unavailable.
    # Only an explicit 01 is reported to the user as "not found" (likely a typo).
    # 02 and anything unrecognised go to manual review rather than rejecting a
    # real business because the registry or provider misbehaved.
    code = str(payload.get("response_code") or "").strip()
    if code == "01":
        raise NotFoundError("We couldn't find that registration number with CAC.")
    if code != "00" or payload.get("status") is False:
        logger.warning("kyb_provider_unavailable provider=prembly code=%s", code[:8] or "missing")
        raise ExternalProviderError("The CAC register is temporarily unavailable.")
    record = payload.get("data")
    if isinstance(record, list):
        record = record[0] if record else None
    if not isinstance(record, dict):
        raise ExternalProviderError("Business lookup returned no company details.")
    name = next((str(record[k]).strip() for k in ("company_name", "companyName", "approvedName", "name")
                 if record.get(k)), "")
    if not name:
        raise ExternalProviderError("Business lookup returned no company name.")
    status = next((str(record[k]) for k in ("company_status", "companyStatus", "status") if record.get(k)), None)
    return CACResult(company_name=name[:255], registration_status=status, people=_people(record))
