"""Merge multiple heads

Revision ID: c95ac29675b8
Revises: 5b6c7d8e9f0a, 18381b41bb1c
Create Date: 2026-02-04 21:12:11.656871

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c95ac29675b8'
down_revision: Union[str, Sequence[str], None] = ('5b6c7d8e9f0a', '18381b41bb1c')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
