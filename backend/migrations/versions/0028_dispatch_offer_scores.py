"""Score and explanation stored with each automatic job offer.

Revision ID: 0028
Revises: 0027
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("dispatch_job_offers", sa.Column("score", sa.Numeric(5, 1), nullable=True))
    op.add_column("dispatch_job_offers", sa.Column("score_details", JSONB(), nullable=True))


def downgrade():
    op.drop_column("dispatch_job_offers", "score_details")
    op.drop_column("dispatch_job_offers", "score")
