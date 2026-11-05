"""Reconcile the legacy KYB table with the business-verification model, and add
CAC registry check results.

The initial table keyed KYB on a required vendor_id and a single document_url,
while the application (like KYC after 0015) keys it on the business owner's
user id with documents in verification_documents. Tailors/designers have no
vendor row, so vendor_id becomes optional.

Revision ID: 0021
Revises: 0020
"""
import sqlalchemy as sa
from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("kyb_verifications", sa.Column("business_owner_user_id", sa.UUID(), nullable=True))
    # Legacy rows: vendor_id points at vendors.id; fall back to the raw value if it held a user id.
    op.execute("""
        UPDATE kyb_verifications AS k
        SET business_owner_user_id = COALESCE(
            (SELECT v.user_id FROM vendors AS v WHERE v.id = k.vendor_id), k.vendor_id)
    """)
    op.alter_column("kyb_verifications", "business_owner_user_id", nullable=False)
    op.create_index("ix_kyb_verifications_business_owner_user_id", "kyb_verifications", ["business_owner_user_id"])
    op.alter_column("kyb_verifications", "vendor_id", existing_type=sa.UUID(), nullable=True)
    op.alter_column("kyb_verifications", "document_url", existing_type=sa.String(1024), nullable=True)
    op.alter_column("kyb_verifications", "business_registration_number", existing_type=sa.String(128), nullable=True)
    for column in (
        sa.Column("provider", sa.String(32), nullable=False, server_default="manual"),
        sa.Column("reviewed_by_user_id", sa.UUID(), nullable=True),
        sa.Column("company_type", sa.String(4), nullable=True),
        sa.Column("verified_company_name", sa.String(255), nullable=True),
        sa.Column("name_match", sa.Boolean(), nullable=True),
    ):
        op.add_column("kyb_verifications", column)
    op.create_index("ix_kyb_verifications_status", "kyb_verifications", ["status"])


def downgrade():
    bind = op.get_bind()
    orphaned = bind.execute(sa.text(
        "SELECT count(*) FROM kyb_verifications WHERE vendor_id IS NULL OR document_url IS NULL"
    )).scalar_one()
    if orphaned:
        raise RuntimeError("Cannot downgrade while KYB records exist without vendor_id or document_url.")
    op.drop_index("ix_kyb_verifications_status", table_name="kyb_verifications")
    for name in ("name_match", "verified_company_name", "company_type", "reviewed_by_user_id", "provider"):
        op.drop_column("kyb_verifications", name)
    op.alter_column("kyb_verifications", "business_registration_number", existing_type=sa.String(128), nullable=False)
    op.alter_column("kyb_verifications", "document_url", existing_type=sa.String(1024), nullable=False)
    op.alter_column("kyb_verifications", "vendor_id", existing_type=sa.UUID(), nullable=False)
    op.drop_index("ix_kyb_verifications_business_owner_user_id", table_name="kyb_verifications")
    op.drop_column("kyb_verifications", "business_owner_user_id")
