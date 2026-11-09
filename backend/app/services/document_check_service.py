"""Tailora's automatic check of an uploaded identity document.

A vision model reads the document (type, name, date of birth, ID number, expiry, legibility, signs of
editing). The reading is then compared, in code, with the account and the NIN details, and turned
into a short note for the admin and the applicant. The model never decides on its own: every rule
is applied here, and a document check alone never approves anyone (see kyc_service).

Privacy: the document image is sent to the configured AI provider (Vertex AI or Groq) for reading.
Nothing it returns is logged. Only the pass/fail of each rule and the note are stored; the note
never contains the ID number.
"""
from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass
from datetime import date

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from app.core.config import settings
from app.services.nin_matching import name_matches

logger = logging.getLogger(__name__)

MAX_DOCUMENT_BYTES = 5 * 1024 * 1024
IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}

PROMPT = """You are checking an identity document uploaded to a Nigerian marketplace.
Read the document in the image and reply with JSON only, using exactly these keys:
{"is_identity_document": true/false, "document_type": "NIN slip" | "National ID card" | "International passport" | "Driver's licence" | "Voter's card" | "Other" | null,
 "full_name": string or null, "date_of_birth": "YYYY-MM-DD" or null, "id_number": string or null,
 "expiry_date": "YYYY-MM-DD" or null, "legible": true/false, "signs_of_editing": true/false, "notes": short string}
Rules: copy names and numbers exactly as printed; use null for anything you can't read clearly;
"signs_of_editing" is true only for visible tampering (mismatched fonts, pasted photo, altered digits),
or if it is a screenshot of a template rather than a real document; "notes" is one sentence about
the photo quality or anything unusual. Do not guess."""


class DocumentReading(BaseModel):
    model_config = ConfigDict(extra="ignore")
    is_identity_document: bool = False
    document_type: str | None = None
    full_name: str | None = None
    date_of_birth: str | None = None
    id_number: str | None = None
    expiry_date: str | None = None
    legible: bool = False
    signs_of_editing: bool = False
    notes: str = ""


@dataclass
class DocumentCheck:
    checks: dict[str, bool | None]  # None: not applicable (e.g. a passport has no NIN)
    passed: bool
    note: str
    provider: str | None


class DocumentCheckUnavailable(Exception):
    pass


def _date(value: str | None) -> date | None:
    try:
        return date.fromisoformat((value or "").strip()[:10])
    except ValueError:
        return None


def _digits(value: str | None) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


def compare(reading: DocumentReading, *, account_name: str, reference_dob: date | None,
            entered_nin: str | None, today: date | None = None) -> DocumentCheck:
    """Apply Tailora's rules to what the model read. Pure: no network, easy to test."""
    today = today or date.today()
    readable = reading.is_identity_document and reading.legible
    doc_dob, expiry = _date(reading.date_of_birth), _date(reading.expiry_date)
    doc_number = _digits(reading.id_number)
    name_ok = bool(reading.full_name) and (name_matches(account_name, reading.full_name)
                                           or name_matches(reading.full_name, account_name))
    checks: dict[str, bool | None] = {
        "document_readable": readable,
        "document_name_matches": readable and name_ok,
        "document_date_of_birth_matches": (None if reference_dob is None
                                           else readable and doc_dob == reference_dob),
        # Only NIN documents carry the 11-digit NIN; a passport or licence number is a different number.
        "document_nin_matches": (None if len(doc_number) != 11 or not entered_nin
                                 else readable and doc_number == entered_nin),
        "document_not_expired": None if expiry is None else expiry >= today,
        "document_not_edited": not reading.signs_of_editing,
    }
    passed = readable and all(v is not False for v in checks.values())

    kind = (reading.document_type or "document").strip()[:40]
    if not readable:
        note = ("Tailora couldn't read this as an identity document. Please upload a clear, well-lit "
                "photo of your NIN slip, national ID card, international passport or driver's licence.")
    elif passed:
        found = ["the name matches your account"]
        if checks["document_date_of_birth_matches"]:
            found.append("the date of birth matches")
        if checks["document_nin_matches"]:
            found.append("the NIN matches")
        if checks["document_not_expired"]:
            found.append("it hasn't expired")
        note = f"Tailora checked your {kind}: " + ", ".join(found) + ", and it shows no signs of editing."
    else:
        problems = []
        if not checks["document_name_matches"]:
            problems.append(f"the name on the {kind} ({(reading.full_name or 'unreadable')[:80]}) doesn't match "
                            f"the name on your account ({account_name[:80]})")
        if checks["document_date_of_birth_matches"] is False:
            problems.append("the date of birth doesn't match")
        if checks["document_nin_matches"] is False:
            problems.append("the NIN on the document doesn't match the NIN you entered")
        if checks["document_not_expired"] is False:
            problems.append(f"the {kind} has expired")
        if checks["document_not_edited"] is False:
            problems.append("the document looks edited")
        note = "Tailora checked your document: " + "; ".join(problems) + ". Please fix this and resubmit."
    return DocumentCheck(checks=checks, passed=passed, note=note[:900], provider=None)


def unavailable_check(reason: str) -> DocumentCheck:
    return DocumentCheck(checks={"document_readable": None}, passed=False,
                         note=f"Tailora couldn't check the document automatically ({reason}). Compare it by hand.",
                         provider=None)


class DocumentCheckService:
    def __init__(self, vertex=None, http_post=None):
        self._vertex = vertex
        self._post = http_post or httpx.post

    @staticmethod
    def available() -> bool:
        return settings.DOCUMENT_AI_CHECK and (
            settings.VERTEX_AI_ENABLED
            or (settings.AI_FALLBACK_PROVIDER.lower() == "groq" and bool(settings.GROQ_API_KEY)))

    def check(self, documents: list[tuple[bytes, str]], *, account_name: str, reference_dob: date | None,
              entered_nin: str | None) -> DocumentCheck:
        if not self.available():
            return unavailable_check("document checking isn't switched on")
        usable = [(data, ctype) for data, ctype in documents
                  if 0 < len(data) <= MAX_DOCUMENT_BYTES and (ctype in IMAGE_TYPES or ctype == "application/pdf")][:2]
        if not usable:
            return unavailable_check("no readable image was uploaded")
        try:
            reading, provider = self._read(usable)
        except DocumentCheckUnavailable:
            return unavailable_check("the reading service is unavailable right now")
        result = compare(reading, account_name=account_name, reference_dob=reference_dob, entered_nin=entered_nin)
        result.provider = provider
        return result

    def _read(self, documents: list[tuple[bytes, str]]) -> tuple[DocumentReading, str]:
        if settings.VERTEX_AI_ENABLED:
            try:
                from google.genai import types

                from app.services.vertex_service import get_vertex_service
                vertex = self._vertex or get_vertex_service()
                parts = [types.Part.from_text(text=PROMPT)] + [
                    types.Part.from_bytes(data=data, mime_type=ctype) for data, ctype in documents]
                return vertex._structured(DocumentReading, parts), "vertex_ai"
            except Exception as exc:  # noqa: BLE001 - provider errors must not leak; fall back.
                logger.warning("document_check_vertex_failed", extra={"error_type": type(exc).__name__})
        images = [(data, ctype) for data, ctype in documents if ctype in IMAGE_TYPES]
        if settings.AI_FALLBACK_PROVIDER.lower() == "groq" and settings.GROQ_API_KEY and images:
            content = [{"type": "text", "text": PROMPT}] + [
                {"type": "image_url", "image_url": {"url": f"data:{ctype};base64,{base64.b64encode(data).decode()}"}}
                for data, ctype in images]
            try:
                response = self._post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                    json={"model": settings.GROQ_VISION_MODEL, "temperature": 0, "max_tokens": 600,
                          "response_format": {"type": "json_object"},
                          "messages": [{"role": "user", "content": content}]},
                    timeout=40.0)
            except httpx.HTTPError as exc:
                raise DocumentCheckUnavailable("network") from exc
            if response.status_code != 200:
                logger.warning("document_check_groq_http status=%d", response.status_code)
                raise DocumentCheckUnavailable("http")
            try:
                text = response.json()["choices"][0]["message"]["content"]
                return DocumentReading.model_validate(json.loads(text)), "groq"
            except (KeyError, IndexError, TypeError, ValueError, ValidationError) as exc:
                raise DocumentCheckUnavailable("invalid") from exc
        raise DocumentCheckUnavailable("none")
