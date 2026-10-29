"""Reconcile legacy KYC table with encrypted-NIN review model.

Revision ID: 0015
Revises: 0014
"""
from alembic import op
import sqlalchemy as sa

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None

def upgrade():
    for name, column in (
        ("id_number_encrypted", sa.Column("id_number_encrypted", sa.Text(), nullable=True)),
        ("nin_verified_full_name", sa.Column("nin_verified_full_name", sa.String(255), nullable=True)),
        ("nin_verified_date_of_birth", sa.Column("nin_verified_date_of_birth", sa.Date(), nullable=True)),
        ("nin_verified_gender", sa.Column("nin_verified_gender", sa.String(16), nullable=True)),
        ("identity_match", sa.Column("identity_match", sa.Boolean(), nullable=True)),
        ("reviewed_by_user_id", sa.Column("reviewed_by_user_id", sa.UUID(), nullable=True)),
    ):
        op.add_column("kyc_verifications", column)
    op.alter_column("kyc_verifications", "id_type", existing_type=sa.String(64),
                    type_=sa.String(32), nullable=True)
    for column, type_ in (("id_number", sa.String(128)), ("document_url", sa.String(1024))):
        op.alter_column("kyc_verifications", column, existing_type=type_, nullable=True)

def downgrade():
    # Refuse to discard encrypted identity fields when records require them.
    bind = op.get_bind()
    count = bind.execute(sa.text(
        "SELECT count(*) FROM kyc_verifications WHERE id_number_encrypted IS NOT NULL"
    )).scalar_one()
    if count:
        raise RuntimeError("Cannot downgrade while encrypted KYC identity records exist.")
    for name in ("reviewed_by_user_id", "identity_match", "nin_verified_gender",
                 "nin_verified_date_of_birth", "nin_verified_full_name", "id_number_encrypted"):
        op.drop_column("kyc_verifications", name)
    op.alter_column("kyc_verifications", "id_type", existing_type=sa.String(32),
                    type_=sa.String(64), nullable=False)
