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
# The app waits up to 60 s for a submission or a re-check (frontend kyc.api / verification.api);
# each reading attempt stays well inside that.
READ_TIMEOUT_SECONDS = 25.0
# PDFs: refuse pages wider or taller than this (points; A0 is about 3370) and render at most this many
# pixels on the long side, so a small file with a huge page can't exhaust memory.
MAX_PDF_PAGE_POINTS = 4000
MAX_RENDER_PIXELS = 2000
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
    checked: bool = True  # False: the document couldn't be read, so the note only explains why


class DocumentCheckUnavailable(Exception):
    pass


def _date(value: str | None) -> date | None:
    try:
        return date.fromisoformat((value or "").strip()[:10])
    except ValueError:
        return None


def _digits(value: str | None) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


NIN_DOCUMENT_WORDS = ("nin", "national id", "national identity")
OTHER_ID_WORDS = ("passport", "driver", "licence", "license", "voter")


def carries_nin(document_type: str | None, doc_number: str) -> bool:
    kind = (document_type or "").strip().lower()
    if any(word in kind for word in NIN_DOCUMENT_WORDS):
        return True
    if any(word in kind for word in OTHER_ID_WORDS):
        return False
    return len(doc_number) == 11  # unknown type: compare when it shows an 11-digit number


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
        # A NIN slip or national ID card must show the entered NIN, readable in full (missing or
        # partly read counts as not matching). Passports, licences and voter's cards carry a
        # different number, so the comparison doesn't apply to them.
        "document_nin_matches": (readable and len(doc_number) == 11 and doc_number == (entered_nin or "")
                                 if carries_nin(reading.document_type, doc_number) else None),
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
                         provider=None, checked=False)


def pdf_first_page_png(data: bytes) -> bytes | None:
    """First page of a PDF as a PNG, so photo-only readers (Groq) can read NIN slips sent as PDFs."""
    try:
        import io

        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(data)
        try:
            if len(pdf) == 0:
                return None
            page = pdf[0]
            width, height = page.get_size()  # PDF points (1/72 inch)
            # A real NIN slip or ID page is at most a few hundred points across. Refuse absurd pages
            # instead of allocating a huge bitmap, and size the render before it is drawn.
            if not (0 < width <= MAX_PDF_PAGE_POINTS and 0 < height <= MAX_PDF_PAGE_POINTS):
                return None
            scale = min(2.0, MAX_RENDER_PIXELS / max(width, height))
            image = page.render(scale=scale).to_pil()
            out = io.BytesIO()
            image.convert("RGB").save(out, format="PNG", optimize=True)
            return out.getvalue()
        finally:
            pdf.close()
    except Exception:  # noqa: BLE001 - a broken or encrypted PDF just can't be read automatically
        return None


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
            kinds = ", ".join(sorted({ctype for _, ctype in documents})) or "no file"
            return unavailable_check(f"the upload isn't a photo or PDF under 5 MB ({kinds})")
        try:
            reading, provider = self._read(usable)
        except DocumentCheckUnavailable as exc:
            return unavailable_check(str(exc))
        result = compare(reading, account_name=account_name, reference_dob=reference_dob, entered_nin=entered_nin)
        result.provider = provider
        return result

    def _read(self, documents: list[tuple[bytes, str]]) -> tuple[DocumentReading, str]:
        """Read with Vertex AI, then Groq. On failure, the exception says why, in words an admin can act
        on (no document content): which service failed and how."""
        problems: list[str] = []
        if settings.VERTEX_AI_ENABLED:
            try:
                from google.genai import types

                from app.services.vertex_service import get_vertex_service
                vertex = self._vertex or get_vertex_service()
                parts = [types.Part.from_text(text=PROMPT)] + [
                    types.Part.from_bytes(data=data, mime_type=ctype) for data, ctype in documents]
                # Bounded wait, so a slow provider can't outlast the app's request (Groq is tried next).
                from concurrent.futures import ThreadPoolExecutor
                from concurrent.futures import TimeoutError as Timeout
                pool = ThreadPoolExecutor(max_workers=1)
                try:
                    reading = pool.submit(vertex._structured, DocumentReading, parts).result(timeout=READ_TIMEOUT_SECONDS)
                except Timeout:
                    raise TimeoutError("timed out") from None
                finally:
                    pool.shutdown(wait=False)
                return reading, "vertex_ai"
            except Exception as exc:  # noqa: BLE001 - provider errors must not leak; fall back.
                logger.warning("document_check_vertex_failed", extra={"error_type": type(exc).__name__})
                problems.append(f"Vertex AI: {'took too long' if isinstance(exc, TimeoutError) else type(exc).__name__}")
        groq_ready = settings.AI_FALLBACK_PROVIDER.lower() == "groq" and bool(settings.GROQ_API_KEY)
        if groq_ready:
            images = []
            for data, ctype in documents:
                if ctype in IMAGE_TYPES:
                    images.append((data, ctype))
                elif ctype == "application/pdf" and (png := pdf_first_page_png(data)):
                    images.append((png, "image/png"))
            if not images:
                problems.append("Groq: the PDF couldn't be turned into an image (it may be encrypted or damaged)")
            else:
                reading = self._groq(images, problems)
                if reading is not None:
                    return reading, "groq"
        raise DocumentCheckUnavailable("; ".join(problems) or "no reading service is configured")

    def _groq(self, images: list[tuple[bytes, str]], problems: list[str]) -> DocumentReading | None:
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
                timeout=READ_TIMEOUT_SECONDS)
        except httpx.TimeoutException:
            problems.append("Groq: took too long")
            return None
        except httpx.HTTPError as exc:
            problems.append(f"Groq: couldn't connect ({type(exc).__name__})")
            return None
        if response.status_code != 200:
            code = ""
            try:
                error = response.json().get("error") or {}
                code = str(error.get("code") or error.get("type") or "")[:60]
            except (ValueError, AttributeError):
                pass
            logger.warning("document_check_groq_http status=%d code=%s", response.status_code, code or "-")
            hint = {401: "the API key was refused", 403: "the API key isn't allowed to use this model",
                    404: f"the model {settings.GROQ_VISION_MODEL} wasn't found",
                    429: "too many requests right now"}.get(response.status_code, "")
            problems.append(f"Groq: HTTP {response.status_code}" + (f", {hint}" if hint else "")
                            + (f" [{code}]" if code else ""))
            return None
        try:
            text = response.json()["choices"][0]["message"]["content"]
            return DocumentReading.model_validate(json.loads(text))
        except (KeyError, IndexError, TypeError, ValueError, ValidationError):
            problems.append("Groq: the reply couldn't be understood")
            return None
