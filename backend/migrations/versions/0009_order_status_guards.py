"""Enforce valid per-order-type lifecycle states without rewriting legacy rows.

Revision ID: 0009
Revises: 0008
"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

CUSTOMER = (
    "pending", "paid", "accepted", "in_production", "ready_for_delivery",
    "shipped", "out_for_delivery", "delivered", "received", "completed",
    "cancelled", "rejected", "refunded",
)
VENDOR = (
    "cart", "checkout", "payment_pending", "paid", "confirmed", "processing",
    "ready_for_pickup", "picked_up", "in_transit", "delivered", "received",
    "completed", "cancelled", "refunded",
)


def _sql_list(values):
    return ", ".join("'" + value + "'" for value in values)


def upgrade():
    bind = op.get_bind()
    condition = (
        f"(order_type = 'customer_order' AND status IN ({_sql_list(CUSTOMER)})) "
        f"OR (order_type = 'vendor_order' AND status IN ({_sql_list(VENDOR)}))"
    )
    # Never rewrite, delete, or silently normalize existing financial rows.
    invalid_count = bind.execute(
        sa.text(f"SELECT count(*) FROM orders WHERE NOT ({condition})")
    ).scalar_one()
    if invalid_count:
        raise RuntimeError(
            "Unrecognized order lifecycle states exist; review records before migration."
        )
    op.create_check_constraint("ck_orders_type_status", "orders", condition)


def downgrade():
    # Removing a validation constraint does not delete data or move money.
    op.drop_constraint("ck_orders_type_status", "orders", type_="check")
