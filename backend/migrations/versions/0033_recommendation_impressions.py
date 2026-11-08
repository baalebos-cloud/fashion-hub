"""Ranked lists shown to shoppers, for the rules-vs-learned ranking test.

Revision ID: 0033
Revises: 0032
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, UUID

revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "recommendation_impressions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("surface", sa.String(24), nullable=False),
        sa.Column("variant", sa.String(16), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("anonymous_id", sa.String(36), nullable=True),
        sa.Column("item_type", sa.String(16), nullable=False),
        sa.Column("item_ids", ARRAY(UUID(as_uuid=True)), nullable=False),
        sa.Column("served_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("user_id IS NOT NULL OR anonymous_id IS NOT NULL", name="ck_recommendation_impressions_actor"),
    )
    op.create_index("ix_recommendation_impressions_surface_time", "recommendation_impressions", ["surface", "served_at"])
    op.create_index("ix_recommendation_impressions_user", "recommendation_impressions", ["user_id"])


def downgrade():
    op.drop_table("recommendation_impressions")
