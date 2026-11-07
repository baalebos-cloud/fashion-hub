"""Multi-stop delivery batches (planned stop order per rider).

Revision ID: 0029
Revises: 0028
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "delivery_batches",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("delivery_partner_id", UUID(as_uuid=True), sa.ForeignKey("delivery_partners.id"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("stops", JSONB(), nullable=False, server_default="[]"),
        sa.Column("total_minutes", sa.Integer(), nullable=True),
        sa.Column("baseline_minutes", sa.Integer(), nullable=True),
        sa.Column("solver", sa.String(16), nullable=True),
        sa.Column("matrix_source", sa.String(32), nullable=True),
        sa.Column("planned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('active', 'completed')", name="ck_delivery_batches_status"),
    )
    op.create_index("ix_delivery_batches_delivery_partner_id", "delivery_batches", ["delivery_partner_id"])
    op.create_index("uq_delivery_batches_active_per_rider", "delivery_batches", ["delivery_partner_id"],
                    unique=True, postgresql_where=sa.text("status = 'active'"))


def downgrade():
    op.drop_index("uq_delivery_batches_active_per_rider", table_name="delivery_batches")
    op.drop_index("ix_delivery_batches_delivery_partner_id", table_name="delivery_batches")
    op.drop_table("delivery_batches")
