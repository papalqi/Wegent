"""add subtasks task_id updated_at index

Revision ID: 36682b4224f7
Revises: 49cca26cf14b
Create Date: 2026-01-12 22:24:37.804198+08:00

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "36682b4224f7"
down_revision: Union[str, Sequence[str], None] = "49cca26cf14b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    if not inspector.has_table("subtasks"):
        return

    index_name = "ix_subtasks_task_id_updated_at"
    existing_indexes = {idx.get("name") for idx in inspector.get_indexes("subtasks")}
    if index_name in existing_indexes:
        return

    op.create_index(index_name, "subtasks", ["task_id", "updated_at"])


def downgrade() -> None:
    """Downgrade schema."""
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    if not inspector.has_table("subtasks"):
        return

    index_name = "ix_subtasks_task_id_updated_at"
    existing_indexes = {idx.get("name") for idx in inspector.get_indexes("subtasks")}
    if index_name not in existing_indexes:
        return

    op.drop_index(index_name, table_name="subtasks")
