"""Learned related items, rebuilt nightly from shopping activity.

Revision ID: 0032
Revises: 0031
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "item_similarities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("item_type", sa.String(16), nullable=False),
        sa.Column("item_id", UUID(as_uuid=True), nullable=False),
        sa.Column("related_id", UUID(as_uuid=True), nullable=False),
        sa.Column("signal", sa.String(24), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("support", sa.Integer(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("item_type", "item_id", "signal", "related_id", name="uq_item_similarities_pair"),
    )
    op.create_index("ix_item_similarities_lookup", "item_similarities", ["item_type", "item_id", "signal"])


def downgrade():
    op.drop_table("item_similarities")
