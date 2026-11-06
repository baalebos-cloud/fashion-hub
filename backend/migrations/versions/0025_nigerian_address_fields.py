"""Nigerian address details on locations: LGA, landmark, nearest bus stop, instructions.

Revision ID: 0025
Revises: 0024
"""
import sqlalchemy as sa
from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None

COLUMNS = (("lga", 128), ("landmark", 255), ("nearest_bus_stop", 255), ("delivery_instructions", 500))


def upgrade():
    for name, length in COLUMNS:
        op.add_column("locations", sa.Column(name, sa.String(length), nullable=True))


def downgrade():
    for name, _ in reversed(COLUMNS):
        op.drop_column("locations", name)
