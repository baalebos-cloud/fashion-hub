"""Delivery proof: one-time pickup/handover codes, delivery event log, package count.

Revision ID: 0024
Revises: 0023
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def _timestamps():
    return [sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)]


def upgrade():
    op.add_column("deliveries", sa.Column("package_count", sa.Integer(), nullable=True))
    op.create_table(
        "delivery_codes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("delivery_id", UUID(as_uuid=True), sa.ForeignKey("deliveries.id"), nullable=False),
        sa.Column("purpose", sa.String(16), nullable=False),
        sa.Column("nonce", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("purpose IN ('pickup', 'handover')", name="ck_delivery_codes_purpose"),
    )
    op.create_index("ix_delivery_codes_delivery_id", "delivery_codes", ["delivery_id"])
    op.create_index("uq_delivery_codes_live", "delivery_codes", ["delivery_id", "purpose"], unique=True,
                    postgresql_where=sa.text("used_at IS NULL AND revoked_at IS NULL"))
    op.create_table(
        "delivery_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("seq", sa.BigInteger(), sa.Identity(), nullable=False, unique=True),
        sa.Column("delivery_id", UUID(as_uuid=True), sa.ForeignKey("deliveries.id"), nullable=False),
        sa.Column("order_id", UUID(as_uuid=True), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("actor_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("actor_role", sa.String(32), nullable=True),
        sa.Column("idempotency_key", sa.String(80), nullable=True),
        sa.Column("details", JSONB(), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_delivery_events_delivery_id", "delivery_events", ["delivery_id"])
    op.create_index("ix_delivery_events_order_id", "delivery_events", ["order_id"])
    op.create_index("uq_delivery_events_idempotency", "delivery_events", ["delivery_id", "idempotency_key"],
                    unique=True, postgresql_where=sa.text("idempotency_key IS NOT NULL"))


def downgrade():
    op.drop_index("uq_delivery_events_idempotency", table_name="delivery_events")
    op.drop_index("ix_delivery_events_order_id", table_name="delivery_events")
    op.drop_index("ix_delivery_events_delivery_id", table_name="delivery_events")
    op.drop_table("delivery_events")
    op.drop_index("uq_delivery_codes_live", table_name="delivery_codes")
    op.drop_index("ix_delivery_codes_delivery_id", table_name="delivery_codes")
    op.drop_table("delivery_codes")
    op.drop_column("deliveries", "package_count")
