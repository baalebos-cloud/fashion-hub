"""Order -> inventory lock order. All allocation changes join the caller's tx.

Payment settlement owns payment -> order -> inventory. Expiry/cancellation
never lock a payment. Terminal allocation rows are retained permanently.
"""
from collections import Counter
from app.core.exceptions import ConflictError
from app.core.timezone import utcnow
from app.models.order import Order
from app.models.order_timeline import OrderTimelineEntry
from app.models.stock_reservation import StockReservation
from app.services.vendor_catalog_service import lock_inventory

SOURCE = 'vendor_catalog_v1'
UNPAID = {'checkout', 'payment_pending'}


class StockReservationService:
    def __init__(self, db):
        self.db = db

    def records(self, order):
        return self.db.query(StockReservation).filter(StockReservation.order_id == order.id).order_by(StockReservation.product_variant_id).populate_existing().all()

    def release(self, order):
        rows = [r for r in self.records(order) if r.status == 'active']
        inventory = lock_inventory(self.db, [r.product_variant_id for r in rows])
        for row in rows:
            inv = inventory.get(str(row.product_variant_id))
            if not inv or inv.quantity_reserved < row.quantity:
                raise ConflictError('Reserved inventory requires reconciliation.')
            inv.quantity_reserved -= row.quantity
            inv.quantity_available += row.quantity
            row.status, row.released_at = 'released', utcnow()
        self.db.flush()

    def cancel_unpaid(self, order, *, note, actor_user_id=None):
        if order.status not in UNPAID:
            raise ConflictError('Only unpaid material orders may be cancelled; paid orders need a refund review.')
        before = order.status
        self.release(order)
        order.status, order.cancelled_at = 'cancelled', utcnow()
        self.db.add(OrderTimelineEntry(order_id=order.id, from_status=before, to_status='cancelled',
                                       actor_user_id=actor_user_id, note=note))
        self.db.flush()

    def active(self, order, *, now=None):
        if order.pricing_source != SOURCE or not order.reservation_expires_at or order.reservation_expires_at <= (now or utcnow()):
            return False
        rows = self.records(order)
        expected = Counter()
        for item in order.items:
            if item.reference_type != 'product_variant' or not item.reference_id:
                return False
            expected[str(item.reference_id)] += item.quantity
        actual = {str(row.product_variant_id): row.quantity for row in rows if row.status == 'active'}
        return bool(expected) and len(actual) == len(rows) and dict(expected) == actual

    def consume(self, order):
        if not self.active(order):
            return False
        rows = self.records(order)
        inventory = lock_inventory(self.db, [r.product_variant_id for r in rows])
        # A competing inventory transaction may have held these locks across
        # the deadline. Evaluate time again before consuming any stock.
        if not self.active(order):
            return False
        for row in rows:
            inv = inventory.get(str(row.product_variant_id))
            if not inv or inv.quantity_reserved < row.quantity:
                raise ConflictError('Reserved inventory requires reconciliation.')
            inv.quantity_reserved -= row.quantity
            row.status, row.consumed_at = 'consumed', utcnow()
        self.db.flush()
        return True

    def expire_one(self, *, now=None):
        now = now or utcnow()
        order = (self.db.query(Order).filter(Order.order_type == 'vendor_order', Order.pricing_source == SOURCE,
                 Order.status.in_(UNPAID), Order.reservation_expires_at <= now)
                 .order_by(Order.reservation_expires_at, Order.id).with_for_update(skip_locked=True).populate_existing().first())
        if not order:
            self.db.commit()
            return False
        try:
            self.cancel_unpaid(order, note='Stock reservation expired.')
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise
