"""Durable payment work and invoice idempotency.

Revision ID: 0003
Revises: 2ab23f38e9c6
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "2ab23f38e9c6"
branch_labels = None
depends_on = None


def upgrade():
    duplicate = op.get_bind().execute(sa.text(
        "SELECT order_id FROM invoices GROUP BY order_id HAVING count(*) > 1 LIMIT 1"
    )).first()
    if duplicate:
        raise RuntimeError("Duplicate invoices require review before migration; see docs/payment-recovery.md")
    # The initial migration uses Boolean, while old create_all development
    # schemas used JSON booleans. Convert either without deleting event rows.
    op.execute("ALTER TABLE payment_transactions ALTER COLUMN processed TYPE boolean USING processed::text::boolean")
    op.drop_index("ix_invoices_order_id", table_name="invoices")
    op.create_index("ix_invoices_order_id", "invoices", ["order_id"], unique=True)
    op.add_column("payments", sa.Column("last_reconciled_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "payment_outbox",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payments.id"), nullable=False),
        sa.Column("dedupe_key", sa.String(128), nullable=False, unique=True),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("attempts >= 0", name="ck_payment_outbox_attempts"),
    )
    op.create_index("ix_payment_outbox_available_at", "payment_outbox", ["available_at"])


def downgrade():
    pending = op.get_bind().execute(sa.text(
        "SELECT 1 FROM payment_outbox WHERE processed_at IS NULL LIMIT 1"
    )).first()
    if pending:
        raise RuntimeError("Drain or explicitly resolve pending payment outbox work before downgrade")
    op.drop_table("payment_outbox")
    op.drop_column("payments", "last_reconciled_at")
    op.drop_index("ix_invoices_order_id", table_name="invoices")
    op.create_index("ix_invoices_order_id", "invoices", ["order_id"], unique=False)
