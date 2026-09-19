"""referrals, payouts, NIN fields, whatsapp number, measurement requirements

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-17

Adds the schema changes for: the referral/commission program, seller
payout tracking, compulsory NIN identity verification, WhatsApp contact
number, and per-design measurement requirements.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- users: whatsapp, home location, referral code ---
    op.add_column("users", sa.Column("whatsapp_number", sa.String(32), nullable=True))
    op.add_column("users", sa.Column("home_location_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("users", sa.Column("referral_code", sa.String(16), nullable=True))
    op.create_unique_constraint("uq_users_referral_code", "users", ["referral_code"])
    op.create_index("ix_users_referral_code", "users", ["referral_code"])

    # --- kyc_verifications: NIN fields ---
    op.add_column("kyc_verifications", sa.Column("nin_verified_full_name", sa.String(255), nullable=True))
    op.add_column("kyc_verifications", sa.Column("nin_verified_date_of_birth", sa.Date(), nullable=True))
    op.add_column("kyc_verifications", sa.Column("nin_verified_gender", sa.String(16), nullable=True))
    op.add_column("kyc_verifications", sa.Column("identity_match", sa.Boolean(), nullable=True))

    # --- designs: measurement requirements ---
    op.add_column("designs", sa.Column("required_measurement_fields", postgresql.ARRAY(sa.String()), nullable=True))

    # --- referrals ---
    op.create_table(
        "referrals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("referrer_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("referred_user_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("referral_code_used", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("qualifying_order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("qualified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("commission_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("commission_currency", sa.String(8), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_referrals_referrer_user_id", "referrals", ["referrer_user_id"])
    op.create_index("ix_referrals_referred_user_id", "referrals", ["referred_user_id"])
    op.create_index("ix_referrals_status", "referrals", ["status"])

    # --- payouts ---
    op.create_table(
        "payouts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("seller_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gross_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("commission_rate", sa.Numeric(5, 4), nullable=False),
        sa.Column("commission_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("net_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False, server_default="NGN"),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_payouts_seller_user_id", "payouts", ["seller_user_id"])

    # --- orders: buyer/seller now returned to clients, no schema change
    # needed here (columns already existed) -- see schemas/order.py.


def downgrade() -> None:
    op.drop_table("payouts")
    op.drop_table("referrals")
    op.drop_column("designs", "required_measurement_fields")
    op.drop_column("kyc_verifications", "identity_match")
    op.drop_column("kyc_verifications", "nin_verified_gender")
    op.drop_column("kyc_verifications", "nin_verified_date_of_birth")
    op.drop_column("kyc_verifications", "nin_verified_full_name")
    op.drop_index("ix_users_referral_code", table_name="users")
    op.drop_constraint("uq_users_referral_code", "users", type_="unique")
    op.drop_column("users", "referral_code")
    op.drop_column("users", "home_location_id")
    op.drop_column("users", "whatsapp_number")
