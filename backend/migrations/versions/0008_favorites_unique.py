"""Prevent concurrent duplicate favorites without removing saved records.

Revision ID: 0008
Revises: 0007
"""
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    # Abort rather than delete customer data when upgrading a legacy database
    # containing duplicates. New installations start with an empty table.
    connection = op.get_bind()
    duplicate = connection.exec_driver_sql("""
        SELECT 1 FROM favorites
        GROUP BY user_id, favorite_type, favorite_ref_id
        HAVING COUNT(*) > 1 LIMIT 1
    """).first()
    if duplicate:
        raise RuntimeError("Duplicate favorites require manual data-preserving reconciliation.")
    op.create_unique_constraint(
        "uq_favorites_owner_kind_reference", "favorites",
        ["user_id", "favorite_type", "favorite_ref_id"],
    )


def downgrade():
    op.drop_constraint("uq_favorites_owner_kind_reference", "favorites", type_="unique")
