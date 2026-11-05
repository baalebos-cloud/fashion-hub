"""Shareable storefront handles for tailors, designers and vendors.

Revision ID: 0018
Revises: 0017
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "storefront_handles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("handle", sa.String(30), nullable=False),
        sa.Column("owner_user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("owner_type", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("owner_type IN ('professional', 'vendor')", name="ck_storefront_handles_owner_type"),
    )
    op.create_index("ix_storefront_handles_handle", "storefront_handles", ["handle"], unique=True)
    op.create_index("ix_storefront_handles_owner_user_id", "storefront_handles", ["owner_user_id"], unique=True)

    # Give every existing shop a link straight away, derived from its business name.
    from app.services.storefront_handles import candidate_handles

    bind = op.get_bind()
    owners = bind.execute(sa.text("""
        SELECT user_id, business_name, 'professional' AS owner_type, created_at FROM professionals
        UNION ALL
        SELECT user_id, business_name, 'vendor' AS owner_type, created_at FROM vendors
        ORDER BY created_at, user_id
    """)).fetchall()
    taken: set[str] = set()
    seen_owners: set[str] = set()
    for user_id, business_name, owner_type, _ in owners:
        if str(user_id) in seen_owners:
            continue
        handle = next(h for h in candidate_handles(business_name, str(user_id)) if h not in taken)
        taken.add(handle)
        seen_owners.add(str(user_id))
        bind.execute(sa.text("""
            INSERT INTO storefront_handles (id, handle, owner_user_id, owner_type)
            VALUES (gen_random_uuid(), :handle, :user_id, :owner_type)
        """), {"handle": handle, "user_id": user_id, "owner_type": owner_type})


def downgrade():
    op.drop_index("ix_storefront_handles_owner_user_id", table_name="storefront_handles")
    op.drop_index("ix_storefront_handles_handle", table_name="storefront_handles")
    op.drop_table("storefront_handles")
