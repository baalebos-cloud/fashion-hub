"""Idempotent log of status updates from external courier companies.

Revision ID: 0030
Revises: 0029
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "courier_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("courier", sa.String(32), nullable=False),
        sa.Column("event_id", sa.String(128), nullable=False),
        sa.Column("external_id", sa.String(128), nullable=False),
        sa.Column("delivery_id", UUID(as_uuid=True), sa.ForeignKey("deliveries.id"), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("applied", sa.String(16), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("details", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("courier", "event_id", name="uq_courier_events_courier_event"),
    )
    op.create_index("ix_courier_events_external_id", "courier_events", ["external_id"])
    op.create_index("ix_courier_events_delivery_id", "courier_events", ["delivery_id"])


def downgrade():
    op.drop_index("ix_courier_events_delivery_id", table_name="courier_events")
    op.drop_index("ix_courier_events_external_id", table_name="courier_events")
    op.drop_table("courier_events")
