"""Each vendor chooses when a stock line counts as low.

Revision ID: 0034
Revises: 0033
"""
import sqlalchemy as sa
from alembic import op

revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None


def upgrade():
    # Existing vendors keep today's fixed rule (10 or fewer counts as low).
    op.add_column("vendors", sa.Column("low_stock_threshold", sa.Integer(), nullable=False, server_default="10"))
    op.create_check_constraint("ck_vendors_low_stock_threshold_range", "vendors",
                               "low_stock_threshold >= 0 AND low_stock_threshold <= 1000000")


def downgrade():
    op.drop_constraint("ck_vendors_low_stock_threshold_range", "vendors", type_="check")
    op.drop_column("vendors", "low_stock_threshold")
