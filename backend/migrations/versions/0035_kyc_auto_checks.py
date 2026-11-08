"""Identity checks: a keyed NIN fingerprint (spot one NIN on several accounts) and the
automatic rule results shown to admins.

Revision ID: 0035
Revises: 0034
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("kyc_verifications", sa.Column("nin_fingerprint", sa.String(64), nullable=True))
    op.create_index("ix_kyc_verifications_nin_fingerprint", "kyc_verifications", ["nin_fingerprint"])
    op.add_column("kyc_verifications", sa.Column("auto_checks", JSONB, nullable=True))


def downgrade():
    op.drop_column("kyc_verifications", "auto_checks")
    op.drop_index("ix_kyc_verifications_nin_fingerprint", table_name="kyc_verifications")
    op.drop_column("kyc_verifications", "nin_fingerprint")
