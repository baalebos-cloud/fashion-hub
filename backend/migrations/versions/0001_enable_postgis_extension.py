"""enable postgis extension

Revision ID: 0001
Revises:
Create Date: 2026-09-12

This is the required first migration: every table using a Geography/
Geometry column (see app/models/location.py) depends on the PostGIS
extension existing in the database before any subsequent migration runs.
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS postgis;")
