"""Automatic seller payouts: bank accounts and transfer tracking on payouts.

Revision ID: 0039
Revises: 0038
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0039"
down_revision = "0038"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "seller_bank_accounts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bank_code", sa.String(16), nullable=False),
        sa.Column("bank_name", sa.String(128), nullable=False),
        sa.Column("account_number_encrypted", sa.Text(), nullable=False),
        sa.Column("account_last4", sa.String(4), nullable=False),
        sa.Column("account_name", sa.String(255), nullable=False),
        sa.Column("name_matches", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("recipient_code", sa.String(64), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_seller_bank_accounts_user_id", "seller_bank_accounts", ["user_id"], unique=True)
    op.add_column("payouts", sa.Column("transfer_reference", sa.String(64), nullable=True))
    op.create_unique_constraint("uq_payouts_transfer_reference", "payouts", ["transfer_reference"])
    op.add_column("payouts", sa.Column("transfer_code", sa.String(64), nullable=True))
    op.add_column("payouts", sa.Column("hold_reason", sa.String(255), nullable=True))
    op.add_column("payouts", sa.Column("failure_reason", sa.String(255), nullable=True))
    op.add_column("payouts", sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("payouts", sa.Column("processing_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    for column in ("processing_at", "attempts", "failure_reason", "hold_reason", "transfer_code"):
        op.drop_column("payouts", column)
    op.drop_constraint("uq_payouts_transfer_reference", "payouts", type_="unique")
    op.drop_column("payouts", "transfer_reference")
    op.drop_index("ix_seller_bank_accounts_user_id", table_name="seller_bank_accounts")
    op.drop_table("seller_bank_accounts")
