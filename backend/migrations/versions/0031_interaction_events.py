"""Shopping activity for learned recommendations, and the per-account opt-out.

Revision ID: 0031
Revises: 0030
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("personalization_enabled", sa.Boolean(), nullable=False,
                                     server_default=sa.true()))
    op.create_table(
        "interaction_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("anonymous_id", sa.String(36), nullable=True),
        sa.Column("event_type", sa.String(24), nullable=False),
        sa.Column("item_type", sa.String(16), nullable=True),
        sa.Column("item_id", UUID(as_uuid=True), nullable=True),
        sa.Column("search_query", sa.String(100), nullable=True),
        sa.Column("source", sa.String(32), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dedupe_key", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("dedupe_key", name="uq_interaction_events_dedupe_key"),
        sa.CheckConstraint("user_id IS NOT NULL OR anonymous_id IS NOT NULL", name="ck_interaction_events_actor"),
        sa.CheckConstraint("(event_type = 'search') = (item_id IS NULL)", name="ck_interaction_events_item"),
    )
    op.create_index("ix_interaction_events_occurred_at", "interaction_events", ["occurred_at"])
    op.create_index("ix_interaction_events_item", "interaction_events", ["item_type", "item_id"])
    op.create_index("ix_interaction_events_user_time", "interaction_events", ["user_id", "occurred_at"])
    op.create_index("ix_interaction_events_anon_time", "interaction_events", ["anonymous_id", "occurred_at"])


def downgrade():
    op.drop_table("interaction_events")
    op.drop_column("users", "personalization_enabled")
