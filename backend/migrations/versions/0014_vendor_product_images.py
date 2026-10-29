"""Material vendor product images.

Revision ID: 0014
Revises: 0013
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("vendor_products", sa.Column("unit_of_measure", sa.String(16), nullable=False, server_default="yard"))
    op.add_column("vendor_products", sa.Column("image_urls", JSONB(), nullable=False,
                                               server_default=sa.text("'[]'::jsonb")))


def downgrade():
    op.drop_column("vendor_products", "image_urls")
    op.drop_column("vendor_products", "unit_of_measure")
