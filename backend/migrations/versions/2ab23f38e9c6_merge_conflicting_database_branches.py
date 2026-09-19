"""Merge conflicting database branches

Revision ID: 2ab23f38e9c6
Revises: 0002, 035e1bd61029
Create Date: 2026-09-18 09:51:33.183723

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '2ab23f38e9c6'
down_revision: Union[str, None] = ('0002', '035e1bd61029')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
