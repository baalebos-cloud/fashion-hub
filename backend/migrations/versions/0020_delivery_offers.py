"""Rider fare offers on delivery requests.

Revision ID: 0020
Revises: 0019
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "delivery_offers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("delivery_request_id", UUID(as_uuid=True), nullable=False),
        sa.Column("delivery_partner_id", UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("eta_to_pickup_minutes", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("delivery_request_id", "delivery_partner_id", name="uq_delivery_offers_request_partner"),
        sa.CheckConstraint("amount > 0", name="ck_delivery_offers_amount_positive"),
        sa.CheckConstraint("status IN ('pending', 'accepted', 'declined', 'withdrawn')",
                           name="ck_delivery_offers_status"),
    )
    op.create_index("ix_delivery_offers_delivery_request_id", "delivery_offers", ["delivery_request_id"])
    op.create_index("ix_delivery_offers_delivery_partner_id", "delivery_offers", ["delivery_partner_id"])
    op.create_index("ix_delivery_offers_status", "delivery_offers", ["status"])


def downgrade():
    op.drop_index("ix_delivery_offers_status", table_name="delivery_offers")
    op.drop_index("ix_delivery_offers_delivery_partner_id", table_name="delivery_offers")
    op.drop_index("ix_delivery_offers_delivery_request_id", table_name="delivery_offers")
    op.drop_table("delivery_offers")
