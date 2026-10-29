"""Sage-inspired delivery incident intake.

Revision ID: 0013
Revises: 0012
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "dispatch_issue_reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("delivery_id", UUID(as_uuid=True), sa.ForeignKey("deliveries.id"), nullable=False),
        sa.Column("courier_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("issue_type", sa.String(40), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("photo_evidence_url", sa.String(1024)),
        sa.Column("latitude", sa.Float()),
        sa.Column("longitude", sa.Float()),
        sa.Column("status", sa.String(24), nullable=False, server_default="OPEN"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("issue_type IN ('CUSTOMER_UNREACHABLE','WRONG_ADDRESS','PACKAGE_DAMAGED','TRAFFIC_ACCIDENT_DELAY','RECIPIENT_REJECTED','VEHICLE_BREAKDOWN')", name="ck_dispatch_issue_type"),
        sa.CheckConstraint("status IN ('OPEN','INVESTIGATING','RESOLVED','REROUTED')", name="ck_dispatch_issue_status"),
    )
    op.create_index("ix_dispatch_issue_reports_delivery_id", "dispatch_issue_reports", ["delivery_id"])
    op.create_index("ix_dispatch_issue_reports_courier_id", "dispatch_issue_reports", ["courier_id"])

def downgrade():
    op.drop_index("ix_dispatch_issue_reports_courier_id", table_name="dispatch_issue_reports")
    op.drop_index("ix_dispatch_issue_reports_delivery_id", table_name="dispatch_issue_reports")
    op.drop_table("dispatch_issue_reports")
