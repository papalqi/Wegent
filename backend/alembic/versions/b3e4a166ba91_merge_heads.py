"""merge heads

Revision ID: b3e4a166ba91
Revises: 36682b4224f7, s9t0u1v2w3x4
Create Date: 2026-01-16 21:17:17.449469+08:00

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3e4a166ba91"
down_revision: Union[str, Sequence[str], None] = ("36682b4224f7", "s9t0u1v2w3x4")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
