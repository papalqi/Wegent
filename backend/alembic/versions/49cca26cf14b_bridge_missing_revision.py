"""Bridge a missing Alembic revision.

Revision ID: 49cca26cf14b
Revises: p6q7r8s9t0u1
Create Date: 2026-01-13

This is a no-op migration used to restore compatibility with databases that
were stamped with a revision id that no longer exists in this repository.
"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "49cca26cf14b"
down_revision: Union[str, Sequence[str], None] = "p6q7r8s9t0u1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""


def downgrade() -> None:
    """Downgrade schema."""
