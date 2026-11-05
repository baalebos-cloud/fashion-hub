"""Sequential, time-limited job offers to riders (auto-dispatch, phase 3).

Revision ID: 0022
Revises: 0021
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "dispatch_job_offers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("delivery_request_id", UUID(as_uuid=True), sa.ForeignKey("delivery_requests.id"), nullable=False),
        sa.Column("delivery_partner_id", UUID(as_uuid=True), sa.ForeignKey("delivery_partners.id"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="offered"),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("distance_km", sa.Numeric(8, 2), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("delivery_request_id", "delivery_partner_id", name="uq_job_offers_request_partner"),
        sa.CheckConstraint("status IN ('offered', 'accepted', 'declined', 'expired', 'withdrawn')",
                           name="ck_job_offers_status"),
    )
    op.create_index("ix_dispatch_job_offers_delivery_request_id", "dispatch_job_offers", ["delivery_request_id"])
    op.create_index("ix_dispatch_job_offers_delivery_partner_id", "dispatch_job_offers", ["delivery_partner_id"])
    op.create_index("ix_dispatch_job_offers_status", "dispatch_job_offers", ["status"])
    op.create_index("ix_dispatch_job_offers_expires_at", "dispatch_job_offers", ["expires_at"])
    # Database-enforced exclusivity: at most one live offer per job, even under concurrent advances.
    op.create_index("uq_job_offers_one_live_per_request", "dispatch_job_offers", ["delivery_request_id"],
                    unique=True, postgresql_where=sa.text("status = 'offered'"))


def downgrade():
    op.drop_index("uq_job_offers_one_live_per_request", table_name="dispatch_job_offers")
    op.drop_index("ix_dispatch_job_offers_expires_at", table_name="dispatch_job_offers")
    op.drop_index("ix_dispatch_job_offers_status", table_name="dispatch_job_offers")
    op.drop_index("ix_dispatch_job_offers_delivery_partner_id", table_name="dispatch_job_offers")
    op.drop_index("ix_dispatch_job_offers_delivery_request_id", table_name="dispatch_job_offers")
    op.drop_table("dispatch_job_offers")
