"""Disputes: problems buyers raise about paid orders.

Revision ID: 0041
Revises: 0040
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0041"
down_revision = "0040"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "disputes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", UUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("opened_by_user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.String(32), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="open"),
        sa.Column("outcome", sa.String(16), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("refund_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("refund_id", UUID(as_uuid=True), nullable=True),
        sa.Column("resolved_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_disputes_order_id", "disputes", ["order_id"])
    op.create_index("ix_disputes_opened_by_user_id", "disputes", ["opened_by_user_id"])
    op.create_index("ix_disputes_status", "disputes", ["status"])
    op.create_index("uq_disputes_one_open_per_order", "disputes", ["order_id"], unique=True,
                    postgresql_where=sa.text("status IN ('open', 'resolving')"))


def downgrade():
    op.drop_index("uq_disputes_one_open_per_order", table_name="disputes")
    op.drop_index("ix_disputes_status", table_name="disputes")
    op.drop_index("ix_disputes_opened_by_user_id", table_name="disputes")
    op.drop_index("ix_disputes_order_id", table_name="disputes")
    op.drop_table("disputes")
