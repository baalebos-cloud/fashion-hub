"""Backfill professional profiles for previously registered tailor/designer accounts.

Revision ID: 0017
Revises: 0016
"""
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade():
    # Preserve existing profiles, verification flags, uploaded content, and all
    # non-professional accounts. PostgreSQL UUID generation is built-in.
    op.execute("""
        INSERT INTO professionals
            (id, user_id, professional_type, business_name, is_verified,
             average_rating, review_count, accepts_new_orders,
             created_at, updated_at)
        SELECT gen_random_uuid(), u.id, u.role, u.full_name, false,
               0, 0, true, now(), now()
        FROM users AS u
        WHERE u.role IN ('tailor', 'designer')
          AND NOT EXISTS (
              SELECT 1 FROM professionals AS p WHERE p.user_id = u.id
          )
    """)


def downgrade():
    # Profile creation represents real user data and must not be erased on
    # rollback. No schema change to reverse.
    pass
