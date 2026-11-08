"""Recommendations PR 3: personal ranking, the rules-vs-learned test, and the admin health report."""
import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user, get_optional_current_user
from app.core.rate_limit import limiter
from app.core.timezone import utcnow
from app.main import app
from app.models.interaction_event import InteractionEvent
from app.models.inventory import Inventory
from app.models.item_similarity import ItemSimilarity
from app.models.product_variant import ProductVariant
from app.models.professional import Professional
from app.models.recommendation_impression import RecommendationImpression
from app.models.vendor import Vendor
from app.models.vendor_product import VendorProduct
from app.services import interaction_service, personal_ranking_service, recommendation_health
from app.services.personal_ranking_service import Assignment


@pytest.fixture()
def client(db):
    limiter.reset()
    current = [None]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: current[0]
    app.dependency_overrides[get_optional_current_user] = lambda: current[0]
    with TestClient(app) as http:
        yield http, current
    app.dependency_overrides.clear()


@pytest.fixture()
def mode(monkeypatch):
    return lambda value: monkeypatch.setattr(settings, "RECOMMENDATIONS_MODE", value)


@pytest.fixture()
def vendor(db, make_user):
    owner = make_user(role="vendor")
    value = Vendor(user_id=owner.id, business_name="Lagos Fabrics", is_verified=True, average_rating=Decimal("4.0"))
    db.add(value)
    db.commit()
    return value


def _product(db, vendor, name, price="1000", *, age_minutes=0):
    product = VendorProduct(vendor_id=vendor.id, name=name, base_price=Decimal(price))
    db.add(product)
    db.flush()
    if age_minutes:
        product.created_at = utcnow() - timedelta(minutes=age_minutes)
    variant = ProductVariant(product_id=product.id, sku="S-" + uuid.uuid4().hex, price=Decimal(price))
    db.add(variant)
    db.flush()
    db.add(Inventory(product_variant_id=variant.id, quantity_available=5, quantity_reserved=0))
    db.commit()
    return product


def _similar(db, item_type, a, b, score=0.9, signal="viewed_together"):
    for x, y in ((a, b), (b, a)):
        db.add(ItemSimilarity(item_type=item_type, item_id=x, related_id=y, signal=signal, score=score,
                              support=3, computed_at=utcnow()))
    db.commit()


def _viewed(db, item_type, item_id, *, user=None, browser=None, source=None, when=None):
    db.add(InteractionEvent(user_id=user.id if user else None, anonymous_id=browser, event_type="view",
                            item_type=item_type, item_id=item_id, source=source, occurred_at=when or utcnow()))
    db.commit()


# ---- assignment ---------------------------------------------------------------------------------

def test_experiment_splits_shoppers_evenly_and_consistently(mode, make_user):
    mode("experiment")
    browsers = [str(uuid.uuid4()) for _ in range(400)]
    variants = [personal_ranking_service.assign(None, b).variant for b in browsers]
    assert 150 < variants.count("learned") < 250
    assert variants == [personal_ranking_service.assign(None, b).variant for b in browsers]


def test_fixed_modes_opt_out_and_untracked_browsers(mode, make_user):
    user = make_user()
    mode("learned")
    assert personal_ranking_service.assign(user, None).variant == "learned"
    mode("rules")
    assert personal_ranking_service.assign(user, None).variant == "rules"
    mode("learned")
    opted_out = personal_ranking_service.assign(make_user(personalization_enabled=False), None)
    assert (opted_out.variant, opted_out.log) == ("rules", False)
    untracked = personal_ranking_service.assign(None, None)
    assert (untracked.variant, untracked.log) == ("rules", False)


# ---- scoring ------------------------------------------------------------------------------------

def test_items_related_to_a_shoppers_history_rank_first(db, vendor, make_user):
    shopper = make_user()
    seen, related, top_rated = (_product(db, vendor, n) for n in ("Seen", "Related", "Top rated"))
    _similar(db, "product", seen.id, related.id)
    _viewed(db, "product", seen.id, user=shopper)
    ranked = personal_ranking_service.score_items(
        db, Assignment("learned", shopper.id, None, True), "product", [(top_rated.id, 5), (related.id, 1)])
    assert [r[0] for r in ranked] == [related.id, top_rated.id]
    assert ranked[0][2] is True and ranked[1][2] is False


def test_without_history_trending_and_rating_decide(db, vendor, make_user):
    quiet, busy = _product(db, vendor, "Quiet"), _product(db, vendor, "Busy")
    for _ in range(3):
        _viewed(db, "product", busy.id, browser=str(uuid.uuid4()))
    ranked = personal_ranking_service.score_items(
        db, Assignment("learned", make_user().id, None, True), "product", [(quiet.id, 4), (busy.id, 4)])
    assert [r[0] for r in ranked] == [busy.id, quiet.id]
    assert not any(r[2] for r in ranked)


# ---- surfaces -----------------------------------------------------------------------------------

PICKED = "/api/v1/recommendations/products/picked-for-you"


def test_picked_for_you_rules_shows_newest_and_logs_the_list(db, vendor, client, mode):
    http, _ = client
    mode("rules")
    older, newer = _product(db, vendor, "Older", age_minutes=60), _product(db, vendor, "Newer")
    browser = str(uuid.uuid4())
    body = http.get(PICKED, params={"browser_id": browser}).json()
    assert body["ranking"] == "rules"
    assert [(i["name"], i["reason"]) for i in body["items"]] == [("Newer", "new_in"), ("Older", "new_in")]
    (impression,) = db.query(RecommendationImpression).all()
    assert (impression.surface, impression.variant, impression.anonymous_id) == ("picked_for_you", "rules", browser)
    assert impression.item_ids == [newer.id, older.id]


def test_picked_for_you_learned_puts_related_items_first(db, vendor, client, mode):
    http, _ = client
    mode("learned")
    seen = _product(db, vendor, "Seen", age_minutes=30)
    related = _product(db, vendor, "Related", age_minutes=60)
    _product(db, vendor, "Newest")
    browser = str(uuid.uuid4())
    _similar(db, "product", seen.id, related.id)
    _viewed(db, "product", seen.id, browser=browser)
    body = http.get(PICKED, params={"browser_id": browser}).json()
    assert body["ranking"] == "learned"
    assert body["items"][0]["name"] == "Related" and body["items"][0]["reason"] == "for_you"


def test_picked_for_you_without_a_browser_id_uses_rules_and_logs_nothing(db, vendor, client, mode):
    http, _ = client
    mode("learned")
    _product(db, vendor, "Lace")
    assert http.get(PICKED).json()["ranking"] == "rules"
    assert db.query(RecommendationImpression).count() == 0


def test_budget_guide_learned_ranking_reorders_in_budget_matches(db, vendor, client, mode, make_user):
    http, current = client
    current[0] = shopper = make_user(role="tailor")
    cheap = _product(db, vendor, "Cheap", "500")
    pricier = _product(db, vendor, "Pricier", "900")
    seen = _product(db, vendor, "Seen", "5000")  # over budget, but its history counts
    _similar(db, "product", seen.id, pricier.id, signal="bought_together")
    _viewed(db, "product", seen.id, user=shopper)

    mode("rules")
    rules = http.get("/api/v1/ai/commerce/recommendations", params={"budget_ngn": 1000}).json()
    assert rules["ranking"] == "rules" and [i["title"] for i in rules["items"]] == ["Cheap", "Pricier"]
    mode("learned")
    learned = http.get("/api/v1/ai/commerce/recommendations", params={"budget_ngn": 1000}).json()
    assert learned["ranking"] == "learned" and [i["title"] for i in learned["items"]] == ["Pricier", "Cheap"]
    assert {(i.surface, i.variant) for i in db.query(RecommendationImpression)} == {
        ("budget_guide", "rules"), ("budget_guide", "learned")}
    assert cheap.id in db.query(RecommendationImpression).filter_by(variant="rules").one().item_ids


def test_tailor_search_learned_ranking_uses_the_shoppers_history(db, client, mode, make_user):
    http, current = client
    current[0] = shopper = make_user()
    pros = []
    for name, rating in (("Star", "5.0"), ("Familiar", "3.0"), ("Seen", "3.0")):
        owner = make_user(role="tailor")
        pro = Professional(user_id=owner.id, professional_type="tailor", is_verified=True,
                           business_name=name, average_rating=Decimal(rating))
        db.add(pro)
        db.commit()
        pros.append(pro)
    star, familiar, seen = pros
    _similar(db, "professional", seen.id, familiar.id)
    _viewed(db, "professional", seen.id, user=shopper)

    mode("rules")
    rules = http.get("/api/v1/professionals", params={"ranked": True}).json()
    assert rules["ranking"] == "rules" and rules["items"][0]["id"] == str(star.id)
    mode("learned")
    learned = http.get("/api/v1/professionals", params={"ranked": True}).json()
    assert learned["ranking"] == "learned" and learned["total"] == 3
    assert learned["items"][0]["id"] == str(familiar.id)
    assert db.query(RecommendationImpression).filter_by(surface="tailor_search").count() == 2
    # Other lists of tailors (onboarding, "near you") keep the fixed order and aren't logged.
    plain = http.get("/api/v1/professionals").json()
    assert plain["ranking"] == "rules" and plain["items"][0]["id"] == str(star.id)
    assert db.query(RecommendationImpression).count() == 2


# ---- privacy ------------------------------------------------------------------------------------

def test_opt_out_and_retention_remove_impressions(db, make_user):
    user = make_user()
    old = RecommendationImpression(surface="picked_for_you", variant="rules", anonymous_id=str(uuid.uuid4()),
                                   item_type="product", item_ids=[uuid.uuid4()],
                                   served_at=utcnow() - timedelta(days=settings.INTERACTION_RETENTION_DAYS + 1))
    mine = RecommendationImpression(surface="picked_for_you", variant="rules", user_id=user.id,
                                    item_type="product", item_ids=[uuid.uuid4()], served_at=utcnow())
    db.add_all([old, mine])
    db.commit()
    interaction_service.purge_expired(db)
    assert db.query(RecommendationImpression).all() == [mine]
    interaction_service.set_personalization(db, user, False)
    assert db.query(RecommendationImpression).count() == 0


# ---- admin health -------------------------------------------------------------------------------

def _impression(db, variant, browser, items, served_at):
    db.add(RecommendationImpression(surface="picked_for_you", variant=variant, anonymous_id=browser,
                                    item_type="product", item_ids=items, served_at=served_at))


def test_health_counts_clicks_from_the_surface_and_conversions(db, vendor, client, make_user):
    http, current = client
    lace = _product(db, vendor, "Lace")
    now = utcnow()
    clicker, buyer, browser_only = (str(uuid.uuid4()) for _ in range(3))
    for browser in (clicker, buyer, browser_only):
        _impression(db, "learned", browser, [lace.id], now - timedelta(hours=2))
    _viewed(db, "product", lace.id, browser=clicker, source="picked_for_you", when=now - timedelta(hours=1))
    _viewed(db, "product", lace.id, browser=browser_only, source="product_page", when=now - timedelta(hours=1))
    db.add(InteractionEvent(anonymous_id=buyer, event_type="add_to_cart", item_type="product", item_id=lace.id,
                            occurred_at=now - timedelta(hours=1)))
    db.commit()

    current[0] = make_user(role="admin")
    report = http.get("/api/v1/admin/recommendations/health").json()
    picked = next(s for s in report["surfaces"] if s["surface"] == "picked_for_you")
    assert picked["learned"]["shown"] == 3
    assert picked["learned"]["clicked"] == 1  # a plain product-page visit isn't a click on the list
    assert picked["learned"]["converted"] == 1
    assert picked["verdict"]["status"] == "collecting"
    assert report["mode"] == settings.RECOMMENDATIONS_MODE


def test_health_declares_a_winner_only_with_enough_lists(db):
    rules = {"shown": 200, "clicked": 10, "converted": 0}
    learned = {"shown": 200, "clicked": 40, "converted": 0}
    assert recommendation_health._verdict(rules, learned)["status"] == "learned_better"
    assert recommendation_health._verdict(learned, rules)["status"] == "rules_better"
    assert recommendation_health._verdict(rules, dict(rules))["status"] == "no_difference"
    assert recommendation_health._verdict({**rules, "shown": 50}, learned)["status"] == "collecting"
