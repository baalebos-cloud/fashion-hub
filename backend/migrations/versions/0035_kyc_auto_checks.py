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
    _backfill_fingerprints()


def _backfill_fingerprints():
    """Fingerprint existing NINs so the duplicate check covers older records. Without the
    identity key this is skipped; the app then fingerprints them on the next submission and
    sends that submission to manual review if any can't be read."""
    from app.core.config import settings
    if not settings.IDENTITY_ENCRYPTION_KEY:
        return
    from app.core.exceptions import ExternalProviderError
    from app.core.identity_encryption import decrypt_identity, identity_fingerprint
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, id_number_encrypted FROM kyc_verifications "
                                "WHERE nin_fingerprint IS NULL AND id_number_encrypted IS NOT NULL")).all()
    for row_id, sealed in rows:
        try:
            fingerprint = identity_fingerprint(decrypt_identity(sealed))
        except ExternalProviderError:
            continue  # unreadable: left for the app to treat conservatively
        bind.execute(sa.text("UPDATE kyc_verifications SET nin_fingerprint = :f WHERE id = :id"), {"f": fingerprint, "id": row_id})


def downgrade():
    op.drop_column("kyc_verifications", "auto_checks")
    op.drop_index("ix_kyc_verifications_nin_fingerprint", table_name="kyc_verifications")
    op.drop_column("kyc_verifications", "nin_fingerprint")
