"""Shareable recipient tracking links (hashed tokens).

Revision ID: 0023
Revises: 0022
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "delivery_share_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", UUID(as_uuid=True), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("created_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("label", sa.String(60), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("access_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_delivery_share_links_order_id", "delivery_share_links", ["order_id"])
    op.create_index("ix_delivery_share_links_token_hash", "delivery_share_links", ["token_hash"], unique=True)


def downgrade():
    op.drop_index("ix_delivery_share_links_token_hash", table_name="delivery_share_links")
    op.drop_index("ix_delivery_share_links_order_id", table_name="delivery_share_links")
    op.drop_table("delivery_share_links")
