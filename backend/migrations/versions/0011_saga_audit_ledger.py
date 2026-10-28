"""Sandbox-only Saga audit log and balanced, immutable journal.

Revision ID: 0011
Revises: 0010
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "saga_step_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", UUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("step_name", sa.String(64), nullable=False),
        sa.Column("payload", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("error_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('pending', 'completed', 'failed', 'review_required')", name="ck_saga_step_status"),
    )
    op.create_index("ix_saga_log_order_created", "saga_step_log", ["order_id", "created_at"])
    op.create_table(
        "ledger_entries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", UUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("event_key", sa.String(128), nullable=False),
        sa.Column("account", sa.String(64), nullable=False),
        sa.Column("direction", sa.String(6), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False, server_default="NGN"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("direction IN ('debit', 'credit')", name="ck_ledger_direction"),
        sa.CheckConstraint("amount_minor > 0", name="ck_ledger_positive"),
        sa.UniqueConstraint("order_id", "event_key", "account", "direction", name="uq_ledger_event_leg"),
    )
    op.create_index("ix_ledger_order_created", "ledger_entries", ["order_id", "created_at"])


def downgrade():
    bind = op.get_bind()
    for table in ("ledger_entries", "saga_step_log"):
        if bind.execute(sa.text(f"SELECT 1 FROM {table} LIMIT 1")).first():
            raise RuntimeError(f"{table} has audit records: refuse destructive rollback.")
    op.drop_index("ix_ledger_order_created", table_name="ledger_entries")
    op.drop_table("ledger_entries")
    op.drop_index("ix_saga_log_order_created", table_name="saga_step_log")
    op.drop_table("saga_step_log")
