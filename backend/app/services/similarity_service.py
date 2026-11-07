"""Builds item_similarities from shopping activity. Runs nightly.

Method (item-to-item co-occurrence, as used by most shops before they need anything heavier):

1. For every shopper (account, or browser ID when signed out), give each item a weight from
   what they did with it: purchase 5, cart add 3, favourite 3, started booking 2, view 1.
   Older activity counts less (weight halves every SIMILARITY_HALF_LIFE_DAYS), and one shopper's
   weight for one item is capped so a single person can't dominate.
2. Two items are related when the same shoppers engaged with both. The pair score is a cosine
   similarity of the two items' shopper weights (0-1), so popular items don't relate to
   everything just by being popular.
3. A pair needs at least SIMILARITY_MIN_SUPPORT different shoppers, which keeps one person's
   browsing (or one bot) from creating a recommendation.

Two signals are built: viewed_together from all activity, bought_together from cart adds and
purchases only. Items are only related to items of the same type. The top SIMILARITY_TOP_N per
item are kept; the table is replaced in one transaction, so readers never see a half-built set.
"""
import math
from collections import defaultdict
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.timezone import utcnow
from app.models.interaction_event import InteractionEvent
from app.models.item_similarity import ItemSimilarity

EVENT_WEIGHTS = {"purchase": 5.0, "add_to_cart": 3.0, "favorite": 3.0, "booking_started": 2.0, "view": 1.0}
BUY_EVENTS = {"purchase", "add_to_cart"}
MAX_WEIGHT_PER_ITEM = 10.0
MAX_ITEMS_PER_SHOPPER = 50  # keeps the pair count bounded for very active shoppers


def _pairs(profiles: dict, min_support: int, top_n: int) -> dict:
    """profiles: shopper -> {(item_type, item_id): weight}. Returns
    (item_type, item_id) -> [(related_id, score, support)] best first."""
    norms: dict = defaultdict(float)
    dot: dict = defaultdict(float)
    support: dict = defaultdict(int)
    for items in profiles.values():
        top = sorted(items.items(), key=lambda kv: -kv[1])[:MAX_ITEMS_PER_SHOPPER]
        for key, weight in top:
            norms[key] += weight * weight
        for index, (a, wa) in enumerate(top):
            for b, wb in top[index + 1:]:
                if a[0] != b[0]:
                    continue  # same item type only
                pair = (a, b) if str(a[1]) < str(b[1]) else (b, a)
                dot[pair] += wa * wb
                support[pair] += 1

    related: dict = defaultdict(list)
    for (a, b), value in dot.items():
        if support[(a, b)] < min_support:
            continue
        score = value / math.sqrt(norms[a] * norms[b])
        related[a].append((b[1], score, support[(a, b)]))
        related[b].append((a[1], score, support[(a, b)]))
    return {key: sorted(rows, key=lambda r: (-r[1], str(r[0])))[:top_n] for key, rows in related.items()}


def rebuild(db: Session) -> dict:
    now = utcnow()
    since = now - timedelta(days=min(settings.SIMILARITY_LOOKBACK_DAYS, settings.INTERACTION_RETENTION_DAYS))
    half_life = settings.SIMILARITY_HALF_LIFE_DAYS

    everything: dict = defaultdict(lambda: defaultdict(float))
    bought: dict = defaultdict(lambda: defaultdict(float))
    rows = (db.query(InteractionEvent.user_id, InteractionEvent.anonymous_id, InteractionEvent.event_type,
                     InteractionEvent.item_type, InteractionEvent.item_id, InteractionEvent.occurred_at)
            .filter(InteractionEvent.occurred_at >= since, InteractionEvent.item_id.isnot(None))
            .yield_per(2000))
    for user_id, anonymous_id, event_type, item_type, item_id, occurred_at in rows:
        base = EVENT_WEIGHTS.get(event_type)
        if base is None:
            continue
        shopper = ("u", user_id) if user_id is not None else ("a", anonymous_id)
        age_days = max((now - occurred_at).total_seconds() / 86400, 0)
        weight = base * 0.5 ** (age_days / half_life)
        key = (item_type, item_id)
        everything[shopper][key] = min(everything[shopper][key] + weight, MAX_WEIGHT_PER_ITEM)
        if event_type in BUY_EVENTS:
            bought[shopper][key] = min(bought[shopper][key] + weight, MAX_WEIGHT_PER_ITEM)

    min_support, top_n = settings.SIMILARITY_MIN_SUPPORT, settings.SIMILARITY_TOP_N
    built = {"viewed_together": _pairs(everything, min_support, top_n),
             "bought_together": _pairs(bought, min_support, top_n)}

    db.query(ItemSimilarity).delete(synchronize_session=False)
    count = 0
    for signal, related in built.items():
        for (item_type, item_id), rows in related.items():
            for related_id, score, pair_support in rows:
                db.add(ItemSimilarity(item_type=item_type, item_id=item_id, related_id=related_id, signal=signal,
                                      score=round(score, 6), support=pair_support, computed_at=now))
                count += 1
    db.commit()
    return {"pairs": count, "shoppers": len(everything)}
