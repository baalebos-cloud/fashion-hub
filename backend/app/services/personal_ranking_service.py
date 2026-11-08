"""Personal ranking, and the rules-vs-learned test that proves (or disproves) it.

Who gets which ranking (assign):
  RECOMMENDATIONS_MODE=rules or learned applies to everyone. In "experiment" each shopper is
  fixed to one side by a hash of their account (or browser ID) and RECOMMENDATIONS_EXPERIMENT,
  so the same person always sees the same ranking. Shoppers who opted out of personalisation,
  or whose browser asks not to be tracked (Privacy-page opt-out, GPC, Do Not Track; see
  tracking_allowed), always get the rules ranking and nothing is logged, signed in or not.

Learned score (score_items), each part 0-1:
  0.60  affinity   -- how related the item is to what this shopper recently engaged with
                      (item_similarities; bought-together counts 1.5x; items they engaged with
                      directly get a smaller boost)
  0.25  trending   -- recent engagement by all shoppers over the last 14 days
  0.15  rating     -- seller rating out of 5
A shopper with no history gets trending + rating, which is still a fair learned baseline.
"""
import hashlib
import uuid
from collections import defaultdict
from datetime import timedelta
from typing import Iterable

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.timezone import utcnow
from app.models.interaction_event import InteractionEvent
from app.models.item_similarity import ItemSimilarity
from app.models.recommendation_impression import RecommendationImpression
from app.models.user import User
from app.services.similarity_service import EVENT_WEIGHTS

WEIGHTS = {"affinity": 0.60, "trending": 0.25, "rating": 0.15}
PROFILE_DAYS = 90
PROFILE_HALF_LIFE_DAYS = 30
TRENDING_DAYS = 14
DIRECT_ENGAGEMENT_FACTOR = 0.5
BOUGHT_TOGETHER_FACTOR = 1.5


class Assignment:
    def __init__(self, variant: str, user_id: uuid.UUID | None, anonymous_id: str | None, log: bool,
                 experiment: str | None = None):
        self.variant, self.user_id, self.anonymous_id, self.log = variant, user_id, anonymous_id, log
        self.experiment = experiment  # set only when randomly assigned in a test

    @property
    def learned(self) -> bool:
        return self.variant == "learned"


def tracking_allowed(request) -> bool:
    """False when this browser asked not to be tracked: the website's own opt-out header
    (Privacy page, GPC or Do Not Track), or the browser's Sec-GPC / DNT headers directly.
    Applies to signed-in shoppers too: signing in is not consent to tracking."""
    headers = request.headers
    return (headers.get("x-tracking-consent", "").lower() != "off"
            and headers.get("sec-gpc") != "1" and headers.get("dnt") != "1")


def assign(user: User | None, anonymous_id: str | None, *, tracking: bool = True) -> Assignment:
    if not tracking:
        return Assignment("rules", None, None, log=False)
    if user is not None and not user.personalization_enabled:
        return Assignment("rules", None, None, log=False)
    actor = str(user.id) if user is not None else anonymous_id
    if not actor:
        return Assignment("rules", None, None, log=False)
    user_id = user.id if user is not None else None
    anon = None if user is not None else anonymous_id
    mode = settings.RECOMMENDATIONS_MODE
    if mode in ("rules", "learned"):
        return Assignment(mode, user_id, anon, log=True)
    digest = hashlib.sha256(f"{settings.RECOMMENDATIONS_EXPERIMENT}:{actor}".encode()).digest()
    return Assignment("learned" if digest[0] % 2 else "rules", user_id, anon, log=True,
                      experiment=settings.RECOMMENDATIONS_EXPERIMENT)


def _profile(db: Session, assignment: Assignment) -> dict[tuple[str, uuid.UUID], float]:
    """(item_type, item_id) -> decayed engagement weight for this shopper."""
    if assignment.user_id is None and assignment.anonymous_id is None:
        return {}
    now = utcnow()
    query = db.query(InteractionEvent.event_type, InteractionEvent.item_type, InteractionEvent.item_id,
                     InteractionEvent.occurred_at).filter(
        InteractionEvent.occurred_at >= now - timedelta(days=PROFILE_DAYS), InteractionEvent.item_id.isnot(None))
    if assignment.user_id is not None:
        query = query.filter(InteractionEvent.user_id == assignment.user_id)
    else:
        query = query.filter(InteractionEvent.user_id.is_(None), InteractionEvent.anonymous_id == assignment.anonymous_id)
    weights: dict = defaultdict(float)
    for event_type, item_type, item_id, occurred_at in query:
        age_days = max((now - occurred_at).total_seconds() / 86400, 0)
        weights[(item_type, item_id)] += EVENT_WEIGHTS.get(event_type, 0) * 0.5 ** (age_days / PROFILE_HALF_LIFE_DAYS)
    return dict(weights)


def _normalise(values: dict) -> dict:
    top = max(values.values(), default=0)
    return {k: v / top for k, v in values.items()} if top > 0 else {k: 0.0 for k in values}


def _affinity(db: Session, profile: dict, item_type: str, candidates: list[uuid.UUID]) -> dict:
    seeds = {item_id: w for (kind, item_id), w in profile.items() if kind == item_type}
    scores = {c: DIRECT_ENGAGEMENT_FACTOR * seeds.get(c, 0.0) for c in candidates}
    if seeds and candidates:
        rows = (db.query(ItemSimilarity.item_id, ItemSimilarity.related_id, ItemSimilarity.score, ItemSimilarity.signal)
                .filter(ItemSimilarity.item_type == item_type, ItemSimilarity.item_id.in_(list(seeds)),
                        ItemSimilarity.related_id.in_(candidates)))
        for seed, related, score, signal in rows:
            factor = BOUGHT_TOGETHER_FACTOR if signal == "bought_together" else 1.0
            scores[related] += seeds[seed] * score * factor
    return _normalise(scores)


def _trending(db: Session, item_type: str, candidates: list[uuid.UUID]) -> dict:
    now = utcnow()
    counts: dict = {c: 0.0 for c in candidates}
    if candidates:
        rows = (db.query(InteractionEvent.item_id, InteractionEvent.event_type, InteractionEvent.occurred_at)
                .filter(InteractionEvent.item_type == item_type, InteractionEvent.item_id.in_(candidates),
                        InteractionEvent.occurred_at >= now - timedelta(days=TRENDING_DAYS)))
        for item_id, event_type, occurred_at in rows:
            age_days = max((now - occurred_at).total_seconds() / 86400, 0)
            counts[item_id] += EVENT_WEIGHTS.get(event_type, 0) * 0.5 ** (age_days / 7)
    return _normalise(counts)


def score_items(db: Session, assignment: Assignment, item_type: str,
                candidates: Iterable[tuple[uuid.UUID, float]]) -> list[tuple[uuid.UUID, float, bool]]:
    """candidates: (item_id, rating 0-5) in the rules order. Returns (item_id, score, personal)
    best first, where personal says the shopper's own history contributed. Ties keep rules order."""
    items = list(candidates)
    ids = [item_id for item_id, _ in items]
    affinity = _affinity(db, _profile(db, assignment), item_type, ids)
    trending = _trending(db, item_type, ids)
    scored = []
    for position, (item_id, rating) in enumerate(items):
        value = (WEIGHTS["affinity"] * affinity[item_id] + WEIGHTS["trending"] * trending[item_id]
                 + WEIGHTS["rating"] * max(0.0, min(float(rating or 0) / 5, 1.0)))
        scored.append((item_id, value, affinity[item_id] > 0, position))
    scored.sort(key=lambda s: (-s[1], s[3]))
    return [(item_id, value, personal) for item_id, value, personal, _ in scored]


def log_impression(db: Session, assignment: Assignment, surface: str, item_type: str, item_ids: list) -> None:
    if not assignment.log or not item_ids:
        return
    db.add(RecommendationImpression(surface=surface, variant=assignment.variant,
                                    assigned_by="experiment" if assignment.experiment else "fixed",
                                    experiment=assignment.experiment, user_id=assignment.user_id,
                                    anonymous_id=assignment.anonymous_id, item_type=item_type,
                                    item_ids=list(item_ids), served_at=utcnow()))
    db.commit()
