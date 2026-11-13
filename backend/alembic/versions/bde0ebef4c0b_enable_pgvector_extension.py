"""enable pgvector extension

Revision ID: bde0ebef4c0b
Revises: 404cf0c76515
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "bde0ebef4c0b"
down_revision: Union[str, Sequence[str], None] = "404cf0c76515"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    # Keep the extension installed: other database objects may depend on it.
    pass
