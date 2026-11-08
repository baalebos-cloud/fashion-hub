"""Recommendations PR 4: free-text design search with checked AI filters and a keyword fallback."""
import time
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.main import app
from app.models.design import Design
from app.models.professional import Professional
from app.services import smart_search_service as smart

SMART = "/api/v1/search/smart"


@pytest.fixture()
def client(db):
    limiter.reset()
    smart._ai_filters_cached.cache_clear()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as http:
        yield http
    app.dependency_overrides.clear()
    smart._ai_filters_cached.cache_clear()


@pytest.fixture()
def designs(db, make_user):
    def add(title, price, description=None, *, verified=True, published=True):
        owner = make_user(role="tailor")
        pro = Professional(user_id=owner.id, professional_type="tailor", is_verified=verified,
                           business_name=f"{title} House")
        db.add(pro)
        db.flush()
        design = Design(professional_id=pro.id, title=title, description=description, base_price=Decimal(price),
                        required_measurement_fields=["chest"], is_published=published)
        db.add(design)
        db.commit()
        return design
    return add


@pytest.fixture()
def ai(monkeypatch):
    """Turn AI search on and control what the provider 'replies'."""
    calls = []

    def use(reply=None, *, error=None, delay=0.0):
        monkeypatch.setattr(settings, "AI_SEARCH_ENABLED", True)

        def fake(text):
            calls.append(text)
            if delay:
                time.sleep(delay)
            if error:
                raise error
            return reply
        import app.integrations.ai.fashion_assistant as fa
        monkeypatch.setattr(fa, "request_search_filters", fake)
        return calls
    return use


@pytest.mark.parametrize("text, keywords, low, high", [
    ("blue agbada under 50k", ["blue", "agbada"], None, 50000),
    ("between 20k and 40k lace kaftan", ["lace", "kaftan"], 20000, 40000),
    ("Senator wear below ₦30,000 for my wedding", ["senator", "wedding"], None, 30000),
    ("aso oke over 100000", ["aso", "oke"], 100000, None),
    ("from 60k to 20k buba", ["buba"], 20000, 60000),
])
def test_keyword_parser_reads_budgets_and_words(text, keywords, low, high):
    filters = smart.keyword_filters(text)
    assert (filters.keywords, filters.min_price, filters.max_price) == (keywords, low, high)


def test_personal_details_are_removed_before_anything_else():
    assert smart.redact("agbada, call 0803 123 4567 or ada@example.com") .split() == ["agbada,", "call", "or"]


@pytest.mark.parametrize("reply, expected", [
    ('{"garment_type": "Agbada", "style_tags": ["blue", "Lace"], "budget_min": null, "budget_max": 50000}',
     (["agbada", "blue", "lace"], None, 50000)),
    ('```json\n{"garment_type": "kaftan", "style_tags": [], "budget_min": 90000, "budget_max": 20000}\n```',
     (["kaftan"], 20000, 90000)),
    ('{"garment_type": null, "style_tags": ["<script>"], "budget_min": -5, "budget_max": "lots"}', None),
    ("I think you want an agbada!", None),
    ('{"garment_type": "agbada", "budget_max": true}', (["agbada"], None, None)),
])
def test_ai_replies_are_checked_strictly(reply, expected):
    filters = smart.parse_ai_reply(reply)
    assert (None if filters is None else (filters.keywords, filters.min_price, filters.max_price)) == expected


def test_search_with_ai_off_uses_keywords_and_ranks_matches(client, designs):
    designs("Blue agbada", "45000", "Hand-finished")
    designs("Agbada", "30000", "Classic white")
    designs("Blue lace gown", "40000")
    designs("Blue agbada deluxe", "90000")  # over budget
    designs("Hidden blue agbada", "10000", verified=False)
    body = client.get(SMART, params={"q": "blue agbada under 50k"}).json()
    assert body["understood_by"] == "keywords"
    assert body["filters"] == {"keywords": ["blue", "agbada"], "min_price": None, "max_price": 50000.0}
    assert [d["title"] for d in body["designs"]] == ["Blue agbada", "Agbada", "Blue lace gown"]
    assert body["designs"][0]["professional_name"] == "Blue agbada House"


def test_search_with_ai_on_uses_its_filters_and_sends_no_personal_details(client, designs, ai):
    designs("Royal kaftan", "35000")
    designs("Agbada", "35000")
    calls = ai('{"garment_type": "kaftan", "style_tags": ["royal"], "budget_min": null, "budget_max": null}')
    body = client.get(SMART, params={"q": "something regal under 40k, my number is 08031234567"}).json()
    assert body["understood_by"] == "ai"
    assert body["filters"] == {"keywords": ["kaftan", "royal"], "min_price": None, "max_price": 40000.0}
    assert [d["title"] for d in body["designs"]] == ["Royal kaftan"]
    assert calls == ["something regal under 40k, my number is"]


@pytest.mark.parametrize("failure", [
    dict(error=RuntimeError("provider down")),
    dict(reply="Sorry, I can't help with that."),
    dict(reply='{"garment_type": "agbada"}', delay=0.5),
])
def test_ai_failure_slowness_or_nonsense_falls_back_to_keywords(client, designs, ai, monkeypatch, failure):
    monkeypatch.setattr(settings, "AI_SEARCH_TIMEOUT_SECONDS", 0.1)
    designs("Lace buba", "20000")
    ai(**failure)
    body = client.get(SMART, params={"q": "lace buba"}).json()
    assert body["understood_by"] == "keywords"
    assert [d["title"] for d in body["designs"]] == ["Lace buba"]


def test_budget_only_and_empty_requests(client, designs):
    designs("Cheap", "10000")
    designs("Dear", "90000")
    assert [d["title"] for d in client.get(SMART, params={"q": "under 20k"}).json()["designs"]] == ["Cheap"]
    nothing = client.get(SMART, params={"q": "please show me"}).json()
    assert nothing["designs"] == [] and nothing["filters"]["keywords"] == []
