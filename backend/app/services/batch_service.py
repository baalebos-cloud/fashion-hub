"""Plan and keep current each rider's multi-stop route (logistics phase 4).

The plan covers the rider's active deliveries: for each, a pickup (unless already collected)
and a drop-off. It starts from the rider's live position when fresh, else their last known
base. Each delivery keeps its own state, codes, events and permissions; the batch only orders
the stops. Replanning runs after anything that changes the set of stops (assignment, pickup,
delivery, release) and never blocks those actions.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.core.timezone import utcnow
from app.models.delivery import Delivery
from app.models.delivery_batch import DeliveryBatch
from app.models.delivery_partner import DeliveryPartner
from app.models.delivery_request import DeliveryRequest
from app.models.location import Location
from app.models.order import Order
from app.models.user import User
from app.services.dispatch_routing import validate_point
from app.services.route_optimizer import Plan, Stop, plan_route

logger = get_logger(__name__)
ACTIVE = ("assigned", "picked_up", "in_transit", "out_for_delivery")
COLLECTED = ("picked_up", "in_transit", "out_for_delivery")


def _point(location: Location | None):
    if location is None:
        return None
    try:
        return validate_point(location.latitude, location.longitude)
    except Exception:  # noqa: BLE001 - a bad pin can't be routed
        return None


def capacity_for(partner: DeliveryPartner) -> int:
    return int(settings.DISPATCH_VEHICLE_CAPACITY.get(partner.vehicle_type or "bike", 1))


class BatchService:
    def __init__(self, db: Session):
        self.db = db

    # ---- planning ----------------------------------------------------------------------------
    def _start_point(self, partner: DeliveryPartner, deliveries: list[Delivery]):
        from app.services.delivery_position import read_position
        for delivery in deliveries:
            position = read_position(delivery.id)
            if position and position.get("freshness") in {"live", "delayed"}:
                return {"latitude": float(position["latitude"]), "longitude": float(position["longitude"])}
        if partner.current_location_id:
            base = _point(self.db.get(Location, partner.current_location_id))
            if base:
                return base
        user = self.db.get(User, partner.user_id)
        return _point(self.db.get(Location, user.home_location_id)) if user and user.home_location_id else None

    def plan_for(self, partner: DeliveryPartner, deliveries: list[Delivery],
                 extra: DeliveryRequest | None = None) -> tuple[Plan, str, dict]:
        """Plan the given deliveries (plus an optional not-yet-assigned request) for a rider."""
        points: list[dict] = []
        stops: list[Stop] = []
        labels: dict[str, dict] = {}

        def add_point(point):
            points.append(point)
            return len(points) - 1

        start = self._start_point(partner, deliveries)
        jobs = [(d, self.db.get(DeliveryRequest, d.delivery_request_id)) for d in deliveries]
        if extra is not None:
            jobs.append((None, extra))
        for delivery, request in jobs:
            if request is None:
                continue
            pickup = _point(self.db.get(Location, request.pickup_location_id))
            dropoff = _point(self.db.get(Location, request.dropoff_location_id))
            if pickup is None or dropoff is None:
                raise ValueError("A stop has no usable map pin.")
            job = str(delivery.id) if delivery else f"request:{request.id}"
            collected = bool(delivery and delivery.status in COLLECTED)
            order = self.db.get(Order, request.order_id)
            for kind, point in (("pickup", pickup), ("dropoff", dropoff)):
                key = f"{job}:{kind}"
                stops.append(Stop(key=key, job=job, kind=kind, point=add_point(point),
                                  done=(kind == "pickup" and collected)))
                labels[key] = {"order_number": order.order_number if order else None,
                               "delivery_id": str(delivery.id) if delivery else None,
                               "request_id": str(request.id)}
        if start is None:
            # Unknown position: start at the first remaining stop (its travel time counts as 0).
            first = next((s for s in stops if not s.done), None)
            start_point = points[first.point] if first else None
        else:
            start_point = start
        if start_point is None:
            return Plan(feasible=True, stops=[], total_minutes=0, solver="none"), "none", labels
        from app.services.route_service import travel_matrix
        matrix, source = travel_matrix([start_point] + points, partner.vehicle_type)
        shifted = [Stop(key=s.key, job=s.job, kind=s.kind, point=s.point + 1, load=s.load, done=s.done) for s in stops]
        plan = plan_route(shifted, start=0, matrix=matrix, capacity=capacity_for(partner),
                          max_minutes=settings.DISPATCH_BATCH_MAX_MINUTES)
        return plan, source, labels

    def active_deliveries(self, partner_id) -> list[Delivery]:
        return (self.db.query(Delivery).filter(Delivery.delivery_partner_id == partner_id,
                                               Delivery.status.in_(ACTIVE))
                .order_by(Delivery.created_at, Delivery.id).all())

    def can_add(self, partner: DeliveryPartner, request: DeliveryRequest) -> Plan:
        return self.plan_for(partner, self.active_deliveries(partner.id), extra=request)[0]

    # ---- persistence ---------------------------------------------------------------------------
    def replan(self, partner_id) -> DeliveryBatch | None:
        """Refresh the rider's active batch. With fewer than two active deliveries the batch is
        closed (there's nothing to sequence). Commits its own changes."""
        partner = self.db.get(DeliveryPartner, partner_id)
        if partner is None:
            return None
        deliveries = self.active_deliveries(partner_id)
        batch = (self.db.query(DeliveryBatch).filter_by(delivery_partner_id=partner_id, status="active")
                 .with_for_update().first())
        if len(deliveries) < 2:
            if batch is not None:
                batch.status = "completed"
                self.db.commit()
            return None
        plan, source, labels = self.plan_for(partner, deliveries)
        if batch is None:
            batch = DeliveryBatch(delivery_partner_id=partner_id, status="active")
            self.db.add(batch)
        batch.stops = [{**stop, **labels.get(stop["key"], {})} for stop in plan.stops]
        batch.total_minutes = plan.total_minutes
        batch.baseline_minutes = plan.baseline_minutes
        batch.solver = plan.solver if plan.feasible else f"{plan.solver}:infeasible"
        batch.matrix_source = source
        batch.planned_at = utcnow()
        self.db.commit()
        return batch


def replan_quietly(db: Session, partner_id) -> None:
    """Best effort: a planning problem must never fail the action that triggered it."""
    if not settings.DISPATCH_MULTISTOP_ENABLED or partner_id is None:
        return
    try:
        BatchService(db).replan(partner_id)
    except Exception:  # noqa: BLE001
        db.rollback()
        logger.warning("batch_replan_failed")


def batch_view(batch: DeliveryBatch | None) -> dict | None:
    if batch is None:
        return None
    saved = None
    if batch.baseline_minutes and batch.total_minutes is not None:
        saved = batch.baseline_minutes - batch.total_minutes
    return {"id": str(batch.id), "stops": batch.stops, "total_minutes": batch.total_minutes,
            "baseline_minutes": batch.baseline_minutes, "minutes_saved": saved, "solver": batch.solver,
            "matrix_source": batch.matrix_source, "estimated": batch.matrix_source in {None, "straight_line_estimate"},
            "planned_at": batch.planned_at}
