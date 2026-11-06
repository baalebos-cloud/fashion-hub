"""Admin two-step sign-in and the activity log.

Revision ID: 0026
Revises: 0025
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "admin_credentials",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("totp_secret_encrypted", sa.String(512), nullable=False),
        sa.Column("totp_enabled_at", sa.DateTime(), nullable=True),
        sa.Column("totp_last_counter", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.add_column("sessions", sa.Column("mfa_verified", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table(
        "activity_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("role", sa.String(32), nullable=True),
        sa.Column("event", sa.String(40), nullable=False),
        sa.Column("method", sa.String(8), nullable=True),
        sa.Column("path", sa.String(255), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(300), nullable=True),
        sa.Column("device_id", sa.String(64), nullable=True),
        sa.Column("details", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    for column in ("user_id", "event", "ip_address", "device_id", "created_at"):
        op.create_index(f"ix_activity_logs_{column}", "activity_logs", [column])


def downgrade():
    for column in ("created_at", "device_id", "ip_address", "event", "user_id"):
        op.drop_index(f"ix_activity_logs_{column}", table_name="activity_logs")
    op.drop_table("activity_logs")
    op.drop_column("sessions", "mfa_verified")
    op.drop_table("admin_credentials")
