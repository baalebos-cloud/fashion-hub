"""First name, middle name and surname on users.

Existing accounts get their parts by splitting full_name (first word, last word, the rest in
between). full_name itself is unchanged and still kept in step with the parts by the app.

Revision ID: 0040
Revises: 0039
"""
import sqlalchemy as sa
from alembic import op

revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("first_name", sa.String(80), nullable=True))
    op.add_column("users", sa.Column("middle_name", sa.String(80), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.String(80), nullable=True))
    # Whitespace-normalised name `n`; first word, last word (if 2+ words), middle words (if 3+).
    op.execute(r"""
        WITH names AS (
            SELECT id, btrim(regexp_replace(full_name, '\s+', ' ', 'g')) AS n FROM users
        )
        UPDATE users u SET
            first_name = NULLIF(left(split_part(names.n, ' ', 1), 80), ''),
            last_name = CASE WHEN position(' ' in names.n) > 0
                             THEN left(regexp_replace(names.n, '^.* ', ''), 80) END,
            middle_name = NULLIF(left(btrim(regexp_replace(regexp_replace(names.n, '^\S+ ?', ''), ' ?\S+$', '')), 80), '')
        FROM names
        WHERE u.id = names.id
    """)


def downgrade():
    op.drop_column("users", "last_name")
    op.drop_column("users", "middle_name")
    op.drop_column("users", "first_name")
