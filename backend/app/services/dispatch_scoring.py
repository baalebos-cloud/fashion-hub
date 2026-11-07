"""Explainable, deterministic rider scoring for automatic offers and dispatcher suggestions.

Hard constraints are applied by the caller first (verified, online, has a vehicle, not busy,
not already offered or reserved, within the radius). This module only ranks riders who pass.

Score (0-100) = weighted sum of factors, each 0..1:
  pickup     time to reach the pickup: road ETA (route_service) for the nearest few by straight
             line, the labelled straight-line ETA for the rest; unknown location scores low
  reliability share of automatic offers accepted in the last 30 days, smoothed so a new rider
             starts near the middle instead of at 0 or 1
  rating     average customer rating / 5 (unrated riders get a neutral 0.7)
  experience completed deliveries, capped at 50
  fairness   fewer jobs assigned today scores higher, spreading work across riders

Same inputs -> same order: ties break on rider id. No AI or randomness. Every result carries
its inputs, per-factor scores, a one-line explanation and the scoring version, and that record
is stored with the offer it led to.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.timezone import utcnow
from app.models.delivery import Delivery
from app.models.delivery_partner import DeliveryPartner
from app.models.dispatch_job_offer import DispatchJobOffer
from app.services.dispatch_pricing import URBAN_SPEED_KMH, road_km
from app.services.dispatch_routing import estimate_straight_line_km

SCORING_VERSION = "dispatch-score-v1"
WEIGHTS = {"pickup": 0.40, "reliability": 0.20, "rating": 0.15, "experience": 0.10, "fairness": 0.15}
PICKUP_ETA_CEILING_MIN = 45  # 45+ minutes to the pickup scores 0 on this factor
NEUTRAL_RATING = 0.7


@dataclass
class ScoredRider:
    partner: DeliveryPartner
    score: float
    straight_line_km: float | None
    pickup_eta_minutes: int | None
    eta_source: str | None
    factors: dict = field(default_factory=dict)
    explanation: str = ""

    def record(self) -> dict:
        return {"version": SCORING_VERSION, "score": self.score, "pickup_eta_minutes": self.pickup_eta_minutes,
                "eta_source": self.eta_source, "straight_line_km": self.straight_line_km,
                "factors": self.factors, "explanation": self.explanation, "scored_at": utcnow().isoformat()}


def _history(db: Session, partner_ids: list) -> tuple[dict, dict, dict]:
    since = utcnow() - timedelta(days=30)
    offers = db.query(DispatchJobOffer.delivery_partner_id, DispatchJobOffer.status, func.count(DispatchJobOffer.id)) \
        .filter(DispatchJobOffer.delivery_partner_id.in_(partner_ids), DispatchJobOffer.created_at >= since,
                DispatchJobOffer.status.in_(["accepted", "declined", "expired"])) \
        .group_by(DispatchJobOffer.delivery_partner_id, DispatchJobOffer.status).all()
    accepted, answered = {}, {}
    for partner_id, status, n in offers:
        answered[partner_id] = answered.get(partner_id, 0) + n
        if status == "accepted":
            accepted[partner_id] = accepted.get(partner_id, 0) + n
    completed = dict(db.query(Delivery.delivery_partner_id, func.count(Delivery.id))
                     .filter(Delivery.status == "delivered", Delivery.delivery_partner_id.in_(partner_ids))
                     .group_by(Delivery.delivery_partner_id).all())
    start_of_day = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today = dict(db.query(Delivery.delivery_partner_id, func.count(Delivery.id))
                 .filter(Delivery.delivery_partner_id.in_(partner_ids), Delivery.created_at >= start_of_day,
                         Delivery.status != "cancelled")
                 .group_by(Delivery.delivery_partner_id).all())
    reliability = {pid: (accepted.get(pid, 0) + 2) / (answered.get(pid, 0) + 3) for pid in partner_ids}
    return reliability, completed, today


def score_riders(db: Session, candidates: list[tuple[DeliveryPartner, dict | None]], pickup: dict | None, *,
                 use_road_eta: bool = True) -> list[ScoredRider]:
    """Rank eligible riders. `candidates` pairs each rider with their base location (or None)."""
    if not candidates:
        return []
    ids = [p.id for p, _ in candidates]
    reliability, completed, today = _history(db, ids)

    straight = {p.id: (estimate_straight_line_km(base, pickup) if base and pickup else None) for p, base in candidates}
    # Road ETAs only for the nearest few, to bound routing calls per offer.
    nearest = sorted((km, str(pid)) for pid, km in straight.items() if km is not None)[:settings.DISPATCH_SCORING_ROUTE_TOP_N]
    road = {}
    if use_road_eta and pickup:
        from app.services.route_service import route
        bases = {str(p.id): base for p, base in candidates}
        vehicles = {str(p.id): p.vehicle_type for p, _ in candidates}
        for _, pid in nearest:
            estimate = route(bases[pid], pickup, vehicles[pid])
            if estimate and estimate.verified:
                road[pid] = estimate

    scored = []
    for partner, _ in candidates:
        pid = str(partner.id)
        km = straight[partner.id]
        if pid in road:
            eta, eta_source = road[pid].duration_minutes, road[pid].source
        elif km is not None:
            speed = URBAN_SPEED_KMH.get(partner.vehicle_type or "bike", URBAN_SPEED_KMH["bike"])
            eta, eta_source = max(1, round(road_km(km) / speed * 60)), "straight_line_estimate"
        else:
            eta, eta_source = None, None
        rating_value = float(partner.average_rating or 0)
        factors = {
            "pickup": (max(0.0, 1 - eta / PICKUP_ETA_CEILING_MIN) if eta is not None else 0.2, eta),
            "reliability": (reliability[partner.id], round(reliability[partner.id], 2)),
            "rating": (rating_value / 5 if rating_value > 0 else NEUTRAL_RATING, rating_value or None),
            "experience": (min(int(completed.get(partner.id, 0)), 50) / 50, int(completed.get(partner.id, 0))),
            "fairness": (1 / (1 + int(today.get(partner.id, 0))), int(today.get(partner.id, 0))),
        }
        total = round(100 * sum(WEIGHTS[name] * value for name, (value, _) in factors.items()), 1)
        detail = {name: {"input": raw, "score": round(value, 3), "weight": WEIGHTS[name]}
                  for name, (value, raw) in factors.items()}
        parts = [f"pickup in about {eta} min ({'road route' if eta_source and eta_source != 'straight_line_estimate' else 'estimate'})"
                 if eta is not None else "location unknown"]
        parts.append(f"accepts {round(reliability[partner.id] * 100)}% of offers")
        parts.append(f"rated {rating_value:.1f}" if rating_value > 0 else "not yet rated")
        parts.append(f"{int(completed.get(partner.id, 0))} deliveries done, {int(today.get(partner.id, 0))} today")
        scored.append(ScoredRider(partner=partner, score=total, straight_line_km=km, pickup_eta_minutes=eta,
                                  eta_source=eta_source, factors=detail, explanation="; ".join(parts)))
    scored.sort(key=lambda s: (-s.score, str(s.partner.id)))
    return scored
