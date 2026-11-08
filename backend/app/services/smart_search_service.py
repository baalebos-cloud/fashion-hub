"""Free-text design search: "blue agbada under 50k" -> checked filters -> the normal search.

1. Personal details (emails, phone numbers) are removed from the text before anything else.
2. When AI_SEARCH_ENABLED, the AI turns the text into filters (garment, style words, budget).
   It only ever produces filters: it never names products, tailors or prices that exist. Its
   answer is checked against strict limits; anything malformed, slow (AI_SEARCH_TIMEOUT_SECONDS)
   or failing is ignored.
3. Otherwise, or as the fallback, a keyword parser reads the budget ("under 50k",
   "between 20k and 40k", "below N30,000") and keeps the meaningful words.
4. The filters run against published designs from verified tailors who accept orders, exactly
   like the existing design search. Designs matching more of the words rank first, then cheaper.

AI calls are bounded: at most AI_WORKERS run at once, and a search that finds them all busy uses
keywords straight away instead of queueing, so slow providers can't build a backlog.
"""
import json
import logging
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass, field
from functools import lru_cache

from sqlalchemy import case, literal, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.design import Design
from app.models.professional import Professional
from app.models.user import User

logger = logging.getLogger(__name__)

MAX_TERMS = 6
MAX_PRICE = 10_000_000
AI_WORKERS = 4

_EXECUTOR = ThreadPoolExecutor(max_workers=AI_WORKERS, thread_name_prefix="smart-search")
_SLOTS = threading.BoundedSemaphore(AI_WORKERS)

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
# Digit runs with spaces, dashes, dots or brackets: 0803 123 4567, (0803) 123-4567, +234.803.123.4567.
_PHONE = re.compile(r"\+?\(?\d[\d\s().-]{6,}\d\)?")
_AMOUNT = r"(?:₦|n|ngn)?\s*(\d+(?:[.,]\d+)*)\s*(k|m)?"
_RANGE = re.compile(rf"(?:between|from)\s+{_AMOUNT}\s+(?:and|to|-)\s+{_AMOUNT}")
_MAX = re.compile(rf"(?:under|below|less than|max(?:imum)?|up to|at most|<)\s*{_AMOUNT}")
_MIN = re.compile(rf"(?:over|above|more than|min(?:imum)?|at least|>)\s*{_AMOUNT}")
_WORD = re.compile(r"[a-z][a-z-]{2,29}")
_STOPWORDS = {
    "the", "and", "for", "with", "want", "need", "looking", "something", "some", "any", "please", "show",
    "find", "get", "buy", "make", "made", "like", "that", "this", "under", "below", "less", "than", "over",
    "above", "more", "between", "from", "budget", "price", "naira", "ngn", "max", "maximum", "minimum",
    "least", "most", "cost", "costs", "cheap", "around", "about", "can", "you", "her", "his", "mine",
    "nice", "good", "outfit", "wear", "within", "upto", "call", "text", "whatsapp", "contact", "number",
    "email", "send", "tell", "let", "know",
}


@dataclass
class Filters:
    keywords: list[str] = field(default_factory=list)
    min_price: float | None = None
    max_price: float | None = None

    def empty(self) -> bool:
        return not self.keywords and self.min_price is None and self.max_price is None


def _phone_or_keep(match: re.Match) -> str:
    # 10+ digits is a phone number; shorter runs are prices like 50000 or 1,500,000.
    return " " if sum(ch.isdigit() for ch in match.group(0)) >= 10 else match.group(0)


def redact(text: str) -> str:
    return _PHONE.sub(_phone_or_keep, _EMAIL.sub(" ", text))


def _amount(number: str, suffix: str | None) -> float | None:
    try:
        value = float(number.replace(",", ""))
    except ValueError:
        return None
    value *= {"k": 1_000, "m": 1_000_000}.get(suffix or "", 1)
    return value if 0 <= value <= MAX_PRICE else None


_PLAIN = re.compile(r"[a-z][a-z -]{1,29}")


def _clean_terms(words, *, strict: bool = False) -> list[str]:
    """Words worth searching for. strict (AI replies): a value that isn't plain words is
    dropped entirely rather than cleaned up."""
    terms: list[str] = []
    for word in words:
        if not isinstance(word, str):
            continue
        if strict and not _PLAIN.fullmatch(word.strip().lower()):
            continue
        for token in _WORD.findall(word.lower()):
            if token not in _STOPWORDS and token not in terms:
                terms.append(token)
    return terms[:MAX_TERMS]


def keyword_filters(text: str) -> Filters:
    lowered = text.lower()
    filters = Filters()
    if match := _RANGE.search(lowered):
        filters.min_price, filters.max_price = _amount(*match.group(1, 2)), _amount(*match.group(3, 4))
        lowered = lowered.replace(match.group(0), " ")
    else:
        if match := _MAX.search(lowered):
            filters.max_price = _amount(*match.group(1, 2))
            lowered = lowered.replace(match.group(0), " ")
        if match := _MIN.search(lowered):
            filters.min_price = _amount(*match.group(1, 2))
            lowered = lowered.replace(match.group(0), " ")
    filters.keywords = _clean_terms([re.sub(r"\d+", " ", lowered)])
    return _ordered(filters)


def _ordered(filters: Filters) -> Filters:
    if filters.min_price is not None and filters.max_price is not None and filters.min_price > filters.max_price:
        filters.min_price, filters.max_price = filters.max_price, filters.min_price
    return filters


def _number(value) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if 0 <= value <= MAX_PRICE else None


def parse_ai_reply(content: str) -> Filters | None:
    """Accept only a JSON object with the expected fields and sane values."""
    match = re.search(r"\{.*\}", content or "", re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    tags = data.get("style_tags")
    words = [data.get("garment_type")] + (tags[:MAX_TERMS] if isinstance(tags, list) else [])
    filters = _ordered(Filters(keywords=_clean_terms(words, strict=True), min_price=_number(data.get("budget_min")),
                               max_price=_number(data.get("budget_max"))))
    return None if filters.empty() else filters


@lru_cache(maxsize=256)
def _ai_filters_cached(text: str) -> Filters | None:
    from app.integrations.ai.fashion_assistant import request_search_filters
    return parse_ai_reply(request_search_filters(text))


def ai_filters(text: str) -> Filters | None:
    if not settings.AI_SEARCH_ENABLED:
        return None
    # Never queue: if every slot is busy (a slow provider), use keywords now.
    if not _SLOTS.acquire(blocking=False):
        logger.warning("smart_search_ai_busy")
        return None

    def run():
        try:
            return _ai_filters_cached(text)
        finally:
            _SLOTS.release()

    try:
        future = _EXECUTOR.submit(run)
    except RuntimeError:
        _SLOTS.release()
        return None
    try:
        return future.result(timeout=settings.AI_SEARCH_TIMEOUT_SECONDS)
    except FutureTimeout:
        future.cancel()  # a call already in progress finishes and frees its slot
        logger.warning("smart_search_ai_timeout")
    except Exception as exc:  # provider down, bad key, network: fall back to keywords
        logger.warning("smart_search_ai_failed", extra={"error_type": type(exc).__name__})
    return None


def understand(query: str) -> tuple[Filters, str]:
    text = " ".join(redact(query).split())[:200]
    if not text:
        return Filters(), "keywords"
    filters = ai_filters(text)
    if filters is not None:
        # The AI may drop a budget the text states plainly; keep the parser's when it has none.
        parsed = keyword_filters(text)
        if filters.min_price is None and filters.max_price is None:
            filters.min_price, filters.max_price = parsed.min_price, parsed.max_price
        return filters, "ai"
    return keyword_filters(text), "keywords"


def search_designs(db: Session, filters: Filters, limit: int = 20) -> list[tuple[Design, Professional]]:
    query = (db.query(Design, Professional)
             .join(Professional, Professional.id == Design.professional_id)
             .join(User, User.id == Professional.user_id)
             .filter(Design.is_published.is_(True), Professional.is_verified.is_(True),
                     User.is_active.is_(True), Professional.accepts_new_orders.is_(True)))
    if filters.min_price is not None:
        query = query.filter(Design.base_price >= filters.min_price)
    if filters.max_price is not None:
        query = query.filter(Design.base_price <= filters.max_price)
    relevance = literal(0)
    if filters.keywords:
        patterns = ["%" + term + "%" for term in filters.keywords]  # terms are [a-z-] only
        query = query.filter(or_(*[Design.title.ilike(p) for p in patterns],
                                 *[Design.description.ilike(p) for p in patterns]))
        # Ranked in the database, so better matches can't be cut off by cheaper partial ones.
        for p in patterns:
            relevance = (relevance + case((Design.title.ilike(p), 2), else_=0)
                         + case((Design.description.ilike(p), 1), else_=0))
    return query.order_by(relevance.desc(), Design.base_price, Design.id).limit(limit).all()
