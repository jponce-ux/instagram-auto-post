"""add thumbnail_key to media_files

Revision ID: add_thumbnail_key_to_media_files
Revises: add_is_verified_to_users
Create Date: 2026-06-09

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "add_thumbnail_key_to_media_files"
down_revision: Union[str, None] = "add_is_verified_to_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("media_files", sa.Column("thumbnail_key", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("media_files", "thumbnail_key")
