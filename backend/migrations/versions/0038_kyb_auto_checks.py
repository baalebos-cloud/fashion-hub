"""Business checks: which automatic-approval rules passed, shown to admins.

Revision ID: 0038
Revises: 0037
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0038"
down_revision = "0037"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("kyb_verifications", sa.Column("auto_checks", JSONB, nullable=True))


def downgrade():
    op.drop_column("kyb_verifications", "auto_checks")
