"""Persist optional ETA for live delivery tracking snapshots.

Revision ID: 0006
Revises: 0005

This is additive and safe for tracking records saved before the ETA feature.
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("delivery_tracking", sa.Column("eta_minutes", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_delivery_tracking_eta_minutes", "delivery_tracking",
        "eta_minutes IS NULL OR eta_minutes BETWEEN 0 AND 1440",
    )


def downgrade():
    existing = op.get_bind().execute(
        sa.text("SELECT 1 FROM delivery_tracking WHERE eta_minutes IS NOT NULL LIMIT 1")
    ).first()
    if existing:
        raise RuntimeError(
            "Delivery ETA data exists; preserve it using a reviewed forward migration."
        )
    op.drop_constraint("ck_delivery_tracking_eta_minutes", "delivery_tracking", type_="check")
    op.drop_column("delivery_tracking", "eta_minutes")
