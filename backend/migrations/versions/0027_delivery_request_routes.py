"""Road route (distance, duration, source, polyline) stored on each delivery request.

Revision ID: 0027
Revises: 0026
"""
import sqlalchemy as sa
from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None

COLUMNS = [
    sa.Column("route_distance_km", sa.Numeric(8, 1), nullable=True),
    sa.Column("route_duration_minutes", sa.Integer(), nullable=True),
    sa.Column("route_source", sa.String(32), nullable=True),
    sa.Column("route_polyline", sa.Text(), nullable=True),
    sa.Column("route_computed_at", sa.DateTime(timezone=True), nullable=True),
]


def upgrade():
    for column in COLUMNS:
        op.add_column("delivery_requests", column)


def downgrade():
    for column in reversed(COLUMNS):
        op.drop_column("delivery_requests", column.name)
