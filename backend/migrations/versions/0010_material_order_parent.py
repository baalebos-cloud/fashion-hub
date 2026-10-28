"""Link vendor material orders to originating customer clothing orders.

Revision ID: 0010
Revises: 0009

Additive metadata only; no payment, escrow, or delivery side effects.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("orders", sa.Column("parent_customer_order_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_orders_parent_customer_order", "orders", "orders",
        ["parent_customer_order_id"], ["id"], ondelete="RESTRICT",
    )
    op.create_index("ix_orders_parent_customer_order_id", "orders", ["parent_customer_order_id"])
    op.create_check_constraint(
        "ck_orders_parent_only_vendor", "orders",
        "parent_customer_order_id IS NULL OR (order_type = 'vendor_order' AND parent_customer_order_id <> id)",
    )


def downgrade():
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT 1 FROM orders WHERE parent_customer_order_id IS NOT NULL LIMIT 1")).first():
        raise RuntimeError("Linked material orders exist; do not discard their audit linkage.")
    op.drop_constraint("ck_orders_parent_only_vendor", "orders", type_="check")
    op.drop_index("ix_orders_parent_customer_order_id", table_name="orders")
    op.drop_constraint("fk_orders_parent_customer_order", "orders", type_="foreignkey")
    op.drop_column("orders", "parent_customer_order_id")
