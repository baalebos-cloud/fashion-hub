"""Add the KYC verification provider column missing from initial schema.

Revision ID: 0012
Revises: 0011
"""
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "kyc_verifications",
        sa.Column("provider", sa.String(length=32), nullable=False, server_default="manual"),
    )


def downgrade():
    op.drop_column("kyc_verifications", "provider")
