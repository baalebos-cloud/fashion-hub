"""PostgreSQL media objects.

Revision ID: 0016
Revises: 0015
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("stored_media",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False, unique=True),
        sa.Column("content_type", sa.String(64), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_stored_media_owner_user_id", "stored_media", ["owner_user_id"])

def downgrade():
    op.drop_index("ix_stored_media_owner_user_id", table_name="stored_media")
    op.drop_table("stored_media")
