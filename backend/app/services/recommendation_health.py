"""Admin "Recommendations health": is learned ranking beating the fixed rules?

For each surface and ranking (rules / learned), over the last REPORT_DAYS, counting only lists
served to shoppers randomly assigned in the current experiment (RECOMMENDATIONS_EXPERIMENT):
  shown       lists served (recommendation_impressions)
  clicked     share of lists where the shopper opened one of the shown items from that surface
              within CLICK_WINDOW (a view whose source is the surface name)
  converted   share of lists where the shopper added a shown item to cart or bought it within
              CONVERSION_WINDOW
A verdict is only given once both sides have MIN_LISTS lists, using a two-proportion z-test on the
click rate at 95% confidence; until then the card says it's too early to tell.
"""
import math
from collections import defaultdict
from datetime import timedelta

from sqlalchemy import String, cast, func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.timezone import utcnow
from app.models.interaction_event import InteractionEvent
from app.models.item_similarity import ItemSimilarity
from app.models.recommendation_impression import SURFACES, VARIANTS, RecommendationImpression

REPORT_DAYS = 30
CLICK_WINDOW = timedelta(hours=24)
CONVERSION_WINDOW = timedelta(days=7)
MIN_LISTS = 100
CONVERSION_EVENTS = ("add_to_cart", "purchase")


def _actor(user_id, anonymous_id):
    return ("u", user_id) if user_id is not None else ("a", anonymous_id)


def _verdict(rules: dict, learned: dict) -> dict:
    n1, n2 = rules["shown"], learned["shown"]
    if min(n1, n2) < MIN_LISTS:
        return {"status": "collecting", "message": f"Too early to tell: each ranking needs {MIN_LISTS} lists shown "
                                                  f"(rules {n1}, learned {n2})."}
    p1, p2 = rules["clicked"] / n1, learned["clicked"] / n2
    pooled = (rules["clicked"] + learned["clicked"]) / (n1 + n2)
    spread = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    z = (p2 - p1) / spread if spread > 0 else 0.0
    if z > 1.96:
        return {"status": "learned_better", "message": f"Learned ranking gets more clicks ({p2:.1%} vs {p1:.1%}), "
                                                       "and the difference is unlikely to be chance."}
    if z < -1.96:
        return {"status": "rules_better", "message": f"The fixed rules get more clicks ({p1:.1%} vs {p2:.1%}). "
                                                     "Consider RECOMMENDATIONS_MODE=rules."}
    return {"status": "no_difference", "message": f"No clear difference yet ({p2:.1%} learned vs {p1:.1%} rules)."}


def summary(db: Session) -> dict:
    now = utcnow()
    since = now - timedelta(days=REPORT_DAYS)
    # Only lists from the current randomised test are compared: not lists served while
    # RECOMMENDATIONS_MODE forced one ranking, and not lists from an earlier (renamed) test.
    impressions = (db.query(RecommendationImpression)
                   .filter(RecommendationImpression.served_at >= since,
                           RecommendationImpression.assigned_by == "experiment",
                           RecommendationImpression.experiment == settings.RECOMMENDATIONS_EXPERIMENT).all())

    actors = {_actor(i.user_id, i.anonymous_id) for i in impressions}
    user_ids = {a[1] for a in actors if a[0] == "u"}
    anon_ids = {a[1] for a in actors if a[0] == "a"}
    events_by_actor: dict = defaultdict(list)
    if impressions:
        query = db.query(InteractionEvent.user_id, InteractionEvent.anonymous_id, InteractionEvent.event_type,
                         InteractionEvent.item_id, InteractionEvent.source, InteractionEvent.occurred_at).filter(
            InteractionEvent.occurred_at >= since, InteractionEvent.item_id.isnot(None))
        for row in query:
            key = _actor(row.user_id, row.anonymous_id)
            if (key[0] == "u" and key[1] in user_ids) or (key[0] == "a" and key[1] in anon_ids):
                events_by_actor[key].append(row)

    stats = {s: {v: {"shown": 0, "clicked": 0, "converted": 0} for v in VARIANTS} for s in SURFACES}
    for imp in impressions:
        if imp.surface not in stats or imp.variant not in VARIANTS:
            continue
        shown = set(imp.item_ids)
        bucket = stats[imp.surface][imp.variant]
        bucket["shown"] += 1
        events = events_by_actor.get(_actor(imp.user_id, imp.anonymous_id), [])
        if any(e.event_type == "view" and e.source == imp.surface and e.item_id in shown
               and imp.served_at <= e.occurred_at <= imp.served_at + CLICK_WINDOW for e in events):
            bucket["clicked"] += 1
        if any(e.event_type in CONVERSION_EVENTS and e.item_id in shown
               and imp.served_at <= e.occurred_at <= imp.served_at + CONVERSION_WINDOW for e in events):
            bucket["converted"] += 1

    surfaces = []
    for surface, by_variant in stats.items():
        rows = {}
        for variant, bucket in by_variant.items():
            shown = bucket["shown"]
            rows[variant] = {**bucket, "click_rate": bucket["clicked"] / shown if shown else None,
                             "conversion_rate": bucket["converted"] / shown if shown else None}
        surfaces.append({"surface": surface, "rules": rows["rules"], "learned": rows["learned"],
                         "verdict": _verdict(rows["rules"], rows["learned"])})

    activity_since = now - timedelta(days=30)
    return {
        "mode": settings.RECOMMENDATIONS_MODE,
        "experiment": settings.RECOMMENDATIONS_EXPERIMENT,
        "report_days": REPORT_DAYS,
        "data": {
            "events_last_30_days": db.query(func.count(InteractionEvent.id))
                                     .filter(InteractionEvent.occurred_at >= activity_since).scalar(),
            "shoppers_last_30_days": db.query(func.count(func.distinct(func.coalesce(
                cast(InteractionEvent.user_id, String), InteractionEvent.anonymous_id))))
                .filter(InteractionEvent.occurred_at >= activity_since).scalar(),
            "related_pairs": db.query(func.count(ItemSimilarity.id)).scalar(),
            "related_items_built_at": db.query(func.max(ItemSimilarity.computed_at)).scalar(),
        },
        "surfaces": surfaces,
    }
