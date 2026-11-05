"""Masked voice call sessions.

Revision ID: 0019
Revises: 0018
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "call_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", UUID(as_uuid=True), nullable=False),
        sa.Column("caller_user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("callee_user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("callee_party", sa.String(16), nullable=False),
        sa.Column("provider", sa.String(24), nullable=False),
        sa.Column("provider_session_id", sa.String(128), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="ringing_caller"),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("callee_party IN ('buyer', 'seller', 'rider')", name="ck_call_sessions_callee_party"),
    )
    op.create_index("ix_call_sessions_order_id", "call_sessions", ["order_id"])
    op.create_index("ix_call_sessions_caller_user_id", "call_sessions", ["caller_user_id"])
    op.create_index("ix_call_sessions_callee_user_id", "call_sessions", ["callee_user_id"])
    op.create_index("ix_call_sessions_provider_session_id", "call_sessions", ["provider_session_id"], unique=True)


def downgrade():
    op.drop_index("ix_call_sessions_provider_session_id", table_name="call_sessions")
    op.drop_index("ix_call_sessions_callee_user_id", table_name="call_sessions")
    op.drop_index("ix_call_sessions_caller_user_id", table_name="call_sessions")
    op.drop_index("ix_call_sessions_order_id", table_name="call_sessions")
    op.drop_table("call_sessions")
