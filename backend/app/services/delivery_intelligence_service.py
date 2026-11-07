"""Delivery intelligence (logistics phase 7): deterministic baselines first, AI last.

Nothing here changes a delivery, a payment or a rider assignment. Everything is advisory, carries
its evidence and version, and works without any AI service.

  readiness()        Is there enough history to train or trust anything? (stated thresholds)
  eta_calibration()  Per vehicle, how much longer real trips take than the route estimate
                     (median of actual/predicted over recent deliveries), with a backtest that
                     compares it to the raw estimate. Usable only when it is measurably better.
  rider_performance(), demand_forecast(), route_efficiency(): plain reports from history.
  recommendations()  Rule-based suggestions, each with evidence, confidence, reasoning, ruleset
                     version and timestamp. A person decides.
  summary()          A plain-language summary of the above. If DELIVERY_AI_SUMMARIES_ENABLED and an
                     AI provider is configured, the wording can be AI-written from the same numbers
                     (no personal data is sent); otherwise the deterministic text is used.
"""
from __future__ import annotations

from datetime import timedelta, timezone
from statistics import median

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.core.timezone import utcnow
from app.models.delivery import Delivery
from app.models.delivery_batch import DeliveryBatch
from app.models.delivery_partner import DeliveryPartner
from app.models.delivery_request import DeliveryRequest
from app.models.dispatch_job_offer import DispatchJobOffer
from app.models.location import Location
from app.models.user import User
from app.services.dispatch_routing import validate_point

logger = get_logger(__name__)
RULESET_VERSION = "delivery-insights-v1"
LOOKBACK_DAYS = 30
MIN_SAMPLES_PER_VEHICLE = 20
# Below these, predictive models aren't worth training; baselines only.
TRAINING_MIN_DELIVERIES = 500
TRAINING_MIN_DAYS = 60
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _aware(value):
    return value if value is None or value.tzinfo else value.replace(tzinfo=timezone.utc)


def _minutes(a, b) -> float | None:
    a, b = _aware(a), _aware(b)
    return None if a is None or b is None else (b - a).total_seconds() / 60


class DeliveryIntelligenceService:
    def __init__(self, db: Session):
        self.db = db

    # ---- data -----------------------------------------------------------------------------------
    def _completed(self, days: int = LOOKBACK_DAYS):
        since = utcnow() - timedelta(days=days)
        return (self.db.query(Delivery, DeliveryRequest, DeliveryPartner)
                .join(DeliveryRequest, DeliveryRequest.id == Delivery.delivery_request_id)
                .outerjoin(DeliveryPartner, DeliveryPartner.id == Delivery.delivery_partner_id)
                .filter(Delivery.status == "delivered", Delivery.delivered_at.is_not(None),
                        Delivery.picked_up_at.is_not(None), Delivery.created_at >= since)
                .order_by(Delivery.created_at, Delivery.id)  # oldest first: the backtest splits by time
                .all())

    def readiness(self) -> dict:
        total = self.db.query(func.count(Delivery.id)).filter(Delivery.status == "delivered").scalar() or 0
        first = self.db.query(func.min(Delivery.created_at)).filter(Delivery.status == "delivered").scalar()
        days = int((utcnow() - _aware(first)).days) if first else 0
        ready = total >= TRAINING_MIN_DELIVERIES and days >= TRAINING_MIN_DAYS
        return {"completed_deliveries": total, "days_of_history": days,
                "needed": {"deliveries": TRAINING_MIN_DELIVERIES, "days": TRAINING_MIN_DAYS},
                "ready_for_models": ready,
                "message": ("Enough history to train and validate predictive models." if ready else
                            f"Baselines only for now: {total} of {TRAINING_MIN_DELIVERIES} completed deliveries and "
                            f"{days} of {TRAINING_MIN_DAYS} days of history needed before training models.")}

    # ---- ETA calibration ------------------------------------------------------------------------
    def _predicted_trip(self, request: DeliveryRequest, vehicle: str | None) -> tuple[float | None, str | None]:
        if request.route_duration_minutes:
            return float(request.route_duration_minutes), request.route_source
        from app.services.route_service import straight_line_estimate
        try:
            a = validate_point(*(lambda loc: (loc.latitude, loc.longitude))(self.db.get(Location, request.pickup_location_id)))
            b = validate_point(*(lambda loc: (loc.latitude, loc.longitude))(self.db.get(Location, request.dropoff_location_id)))
        except Exception:  # noqa: BLE001
            return None, None
        estimate = straight_line_estimate(a, b, vehicle, None) if a and b else None
        return (float(estimate.duration_minutes), estimate.source) if estimate and estimate.duration_minutes else (None, None)

    def eta_calibration(self) -> dict:
        samples: dict[str, list[tuple[float, float]]] = {}
        for delivery, request, partner in self._completed():
            actual = _minutes(delivery.picked_up_at, delivery.delivered_at)
            vehicle = (partner.vehicle_type if partner else None) or "bike"
            predicted, _ = self._predicted_trip(request, vehicle)
            if actual is None or predicted is None or actual <= 0 or actual > 600:
                continue
            samples.setdefault(vehicle, []).append((predicted, actual))
        result = {}
        for vehicle, pairs in samples.items():
            n = len(pairs)
            if n < MIN_SAMPLES_PER_VEHICLE:
                result[vehicle] = {"samples": n, "factor": None, "usable": False,
                                   "reason": f"needs {MIN_SAMPLES_PER_VEHICLE} deliveries"}
                continue
            # Backtest honestly: learn the factor on the older half, score on the newer half.
            split = n // 2
            train, test = pairs[:split], pairs[split:]
            factor = median(a / p for p, a in train)
            mae_raw = sum(abs(a - p) for p, a in test) / len(test)
            mae_cal = sum(abs(a - p * factor) for p, a in test) / len(test)
            usable = mae_cal < mae_raw
            result[vehicle] = {"samples": n, "factor": round(median(a / p for p, a in pairs), 2),
                               "backtest": {"tested_on": len(test), "mean_error_minutes_raw": round(mae_raw, 1),
                                            "mean_error_minutes_calibrated": round(mae_cal, 1)},
                               "usable": usable,
                               "reason": None if usable else "not better than the raw estimate on recent deliveries"}
        return {"version": RULESET_VERSION, "lookback_days": LOOKBACK_DAYS, "by_vehicle": result,
                "enabled": bool(settings.DELIVERY_ETA_CALIBRATION_ENABLED), "generated_at": utcnow().isoformat()}

    def calibrated_minutes(self, minutes: int | None, vehicle: str | None) -> tuple[int | None, bool]:
        """Apply the learned factor only when switched on and validated for this vehicle."""
        if minutes is None or not settings.DELIVERY_ETA_CALIBRATION_ENABLED:
            return minutes, False
        entry = self.eta_calibration()["by_vehicle"].get(vehicle or "bike")
        if not entry or not entry.get("usable") or not entry.get("factor"):
            return minutes, False
        return max(1, round(minutes * entry["factor"])), True

    # ---- reports --------------------------------------------------------------------------------
    def rider_performance(self) -> list[dict]:
        since = utcnow() - timedelta(days=LOOKBACK_DAYS)
        rows = {}
        for delivery, request, partner in self._completed():
            if partner is None:
                continue
            entry = rows.setdefault(partner.id, {"pickup": [], "trip": [], "on_time": 0, "with_estimate": 0, "count": 0})
            entry["count"] += 1
            pickup = _minutes(delivery.created_at, delivery.picked_up_at)
            trip = _minutes(delivery.picked_up_at, delivery.delivered_at)
            if pickup is not None:
                entry["pickup"].append(pickup)
            if trip is not None:
                entry["trip"].append(trip)
                predicted, _ = self._predicted_trip(request, partner.vehicle_type)
                if predicted:
                    entry["with_estimate"] += 1
                    entry["on_time"] += trip <= predicted * 1.5 + 15
        offers = {}
        for partner_id, status, n in (self.db.query(DispatchJobOffer.delivery_partner_id, DispatchJobOffer.status,
                                                    func.count(DispatchJobOffer.id))
                                      .filter(DispatchJobOffer.created_at >= since)
                                      .group_by(DispatchJobOffer.delivery_partner_id, DispatchJobOffer.status)):
            offers.setdefault(partner_id, {})[status] = n
        result = []
        for partner_id, entry in rows.items():
            partner = self.db.get(DeliveryPartner, partner_id)
            user = self.db.get(User, partner.user_id) if partner else None
            answered = sum(offers.get(partner_id, {}).get(s, 0) for s in ("accepted", "declined", "expired"))
            result.append({
                "partner_id": str(partner_id), "first_name": ((user.full_name or "Rider").split(" ")[0]) if user else "Rider",
                "deliveries": entry["count"],
                "median_minutes_to_pickup": round(median(entry["pickup"])) if entry["pickup"] else None,
                "median_trip_minutes": round(median(entry["trip"])) if entry["trip"] else None,
                "on_time_share": round(entry["on_time"] / entry["with_estimate"], 2) if entry["with_estimate"] else None,
                "offer_acceptance": round(offers.get(partner_id, {}).get("accepted", 0) / answered, 2) if answered else None,
                "rating": float(partner.average_rating or 0) if partner else None,
            })
        result.sort(key=lambda r: (-r["deliveries"], r["first_name"]))
        return result

    def demand_forecast(self) -> dict:
        """Average delivery requests per hour of the week over the last 4 weeks (seasonal naive).
        Times are in UTC+1 (West Africa Time)."""
        weeks = 4
        since = utcnow() - timedelta(weeks=weeks)
        counts: dict[tuple[int, int], int] = {}
        for (created,) in self.db.query(DeliveryRequest.created_at).filter(DeliveryRequest.created_at >= since):
            local = _aware(created) + timedelta(hours=1)
            key = (local.weekday(), local.hour)
            counts[key] = counts.get(key, 0) + 1
        now = utcnow() + timedelta(hours=1)
        next_24 = []
        for step in range(24):
            moment = now + timedelta(hours=step)
            key = (moment.weekday(), moment.hour)
            next_24.append({"day": DAYS[key[0]], "hour": key[1], "expected_jobs": round(counts.get(key, 0) / weeks, 1)})
        busiest = sorted(counts.items(), key=lambda kv: -kv[1])[:3]
        return {"method": "4-week average per hour of week", "timezone": "WAT (UTC+1)", "next_24_hours": next_24,
                "busiest_hours": [{"day": DAYS[d], "hour": h, "average_jobs": round(n / weeks, 1)} for (d, h), n in busiest],
                "sample_requests": sum(counts.values())}

    def route_efficiency(self) -> dict:
        since = utcnow() - timedelta(days=LOOKBACK_DAYS)
        batches = self.db.query(DeliveryBatch).filter(DeliveryBatch.created_at >= since,
                                                      DeliveryBatch.baseline_minutes.is_not(None)).all()
        saved = [b.baseline_minutes - b.total_minutes for b in batches if b.total_minutes is not None]
        ratios = []
        for delivery, request, partner in self._completed():
            actual = _minutes(delivery.picked_up_at, delivery.delivered_at)
            predicted, _ = self._predicted_trip(request, partner.vehicle_type if partner else None)
            if actual and predicted:
                ratios.append(actual / predicted)
        return {"multistop_routes": len(batches), "planned_minutes_saved_total": sum(saved),
                "median_actual_vs_estimated_trip": round(median(ratios), 2) if ratios else None,
                "trips_measured": len(ratios)}

    # ---- recommendations and summary ------------------------------------------------------------
    def recommendations(self) -> list[dict]:
        now = utcnow().isoformat()
        out = []

        def add(code, recommendation, evidence, confidence, reasoning):
            out.append({"code": code, "recommendation": recommendation, "evidence": evidence, "confidence": confidence,
                        "reasoning": reasoning, "version": RULESET_VERSION, "generated_at": now,
                        "advisory": True})

        readiness = self.readiness()
        if not readiness["ready_for_models"]:
            add("keep_baselines", "Keep using rule-based estimates; don't switch on predictive models yet.",
                {"completed_deliveries": readiness["completed_deliveries"], "days": readiness["days_of_history"]},
                "high", readiness["message"])
        forecast = self.demand_forecast()
        online = self.db.query(func.count(DeliveryPartner.id)).filter(DeliveryPartner.is_verified.is_(True),
                                                                     DeliveryPartner.is_available.is_(True)).scalar() or 0
        peak = max(forecast["next_24_hours"], key=lambda h: h["expected_jobs"]) if forecast["next_24_hours"] else None
        if peak and peak["expected_jobs"] >= 1 and online < peak["expected_jobs"]:
            add("rider_supply", f"Ask more riders to be online around {peak['hour']:02d}:00 on {peak['day']}.",
                {"expected_jobs_that_hour": peak["expected_jobs"], "riders_online_now": online},
                "medium" if forecast["sample_requests"] >= 50 else "low",
                "That hour has averaged more jobs than riders online now (4-week history).")
        calibration = self.eta_calibration()
        for vehicle, entry in calibration["by_vehicle"].items():
            if entry.get("usable") and not calibration["enabled"]:
                add("eta_calibration", f"Consider switching on ETA calibration ({vehicle} trips take {entry['factor']}x the estimate).",
                    entry["backtest"], "medium",
                    "On recent deliveries the calibrated ETA had a smaller average error than the raw estimate.")
        for rider in self.rider_performance():
            if rider["deliveries"] >= 10 and rider["on_time_share"] is not None and rider["on_time_share"] < 0.6:
                add("rider_coaching", f"Check in with {rider['first_name']} about late deliveries.",
                    {"deliveries": rider["deliveries"], "on_time_share": rider["on_time_share"]}, "medium",
                    "Fewer than 60% of their recent trips finished within 1.5x the estimate plus 15 minutes.")
        return out

    def summary(self) -> dict:
        readiness, forecast = self.readiness(), self.demand_forecast()
        efficiency, recs = self.route_efficiency(), self.recommendations()
        text = (f"{readiness['completed_deliveries']} deliveries completed so far ({readiness['days_of_history']} days of history). "
                f"Trips take a median {efficiency['median_actual_vs_estimated_trip'] or 'unknown'}x the estimated time "
                f"across {efficiency['trips_measured']} measured trips. "
                + (f"Busiest time: {forecast['busiest_hours'][0]['day']} {forecast['busiest_hours'][0]['hour']:02d}:00. "
                   if forecast["busiest_hours"] else "No demand pattern yet. ")
                + (f"{len(recs)} suggestion{'s' if len(recs) != 1 else ''} below." if recs else "No suggestions right now."))
        source = "rules"
        if settings.DELIVERY_AI_SUMMARIES_ENABLED:
            try:
                from app.integrations.ai.llm_client import ChatMessage, LLMClient
                reply = LLMClient().complete([
                    ChatMessage("system", "Rewrite these delivery operations facts as a short, plain summary for a "
                                          "dispatcher in Nigeria. Use only the facts given. Don't invent numbers."),
                    ChatMessage("user", text),
                ], max_tokens=200)
                if reply.content.strip():
                    text, source = reply.content.strip(), f"ai:{settings.AI_PROVIDER}"
            except Exception:  # noqa: BLE001 - AI is optional; the rule-based text stands
                logger.warning("delivery_ai_summary_failed")
        return {"summary": text, "source": source, "version": RULESET_VERSION, "generated_at": utcnow().isoformat()}
