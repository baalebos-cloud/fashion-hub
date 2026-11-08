"""In-app calls: room name and answered/ended times on call_sessions.

Revision ID: 0036
Revises: 0035
"""
import sqlalchemy as sa
from alembic import op

revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("call_sessions", sa.Column("room_name", sa.String(64), nullable=True))
    op.add_column("call_sessions", sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("call_sessions", sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True))
    # Finding someone's ringing or live call is the hot path.
    op.create_index("ix_call_sessions_callee_status", "call_sessions", ["callee_user_id", "status"])


def downgrade():
    op.drop_index("ix_call_sessions_callee_status", table_name="call_sessions")
    op.drop_column("call_sessions", "ended_at")
    op.drop_column("call_sessions", "answered_at")
    op.drop_column("call_sessions", "room_name")
