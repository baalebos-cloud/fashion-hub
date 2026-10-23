"""Add the ETA field used by the delivery GPS tracking model.

Revision ID: 0006
Revises: 0005
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    # Nullable for existing delivery snapshots. No default ETA is invented.
    op.add_column("delivery_tracking", sa.Column("eta_minutes", sa.Integer(), nullable=True))


def downgrade():
    op.drop_column("delivery_tracking", "eta_minutes")
