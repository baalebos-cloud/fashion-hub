"""Seed editable marketplace taxonomy without changing any existing records.

Revision ID: 0007
Revises: 0006

The references are system defaults, not listings or verified professionals.
Downgrade deliberately preserves categories so previously published products
cannot be orphaned during a rollback.
"""
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        INSERT INTO categories (id, name, slug)
        VALUES
          (gen_random_uuid(), 'Native Wear', 'native-wear'),
          (gen_random_uuid(), 'Suits', 'suits'),
          (gen_random_uuid(), 'Bridal', 'bridal'),
          (gen_random_uuid(), 'Agbada', 'agbada'),
          (gen_random_uuid(), 'Ankara', 'ankara'),
          (gen_random_uuid(), 'Kaftan', 'kaftan'),
          (gen_random_uuid(), 'Corporate Wear', 'corporate-wear'),
          (gen_random_uuid(), 'Casual Wear', 'casual-wear')
        ON CONFLICT DO NOTHING
    """)
    op.execute("""
        INSERT INTO vendor_categories (id, name, slug)
        VALUES
          (gen_random_uuid(), 'Fabrics', 'fabrics'),
          (gen_random_uuid(), 'Buttons', 'buttons'),
          (gen_random_uuid(), 'Zippers', 'zippers'),
          (gen_random_uuid(), 'Threads', 'threads'),
          (gen_random_uuid(), 'Linings', 'linings'),
          (gen_random_uuid(), 'Accessories', 'accessories')
        ON CONFLICT DO NOTHING
    """)


def downgrade():
    # Category rows may be referenced by live products or used in search.
    # Never delete user-visible taxonomy in a rollback.
    pass
