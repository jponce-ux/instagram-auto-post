"""add_scheduled_at_to_posts

Revision ID: add_scheduled_at_to_posts
Revises: add_media_files_and_posts
Create Date: 2026-04-05

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "add_scheduled_at_to_posts"
down_revision: Union[str, None] = "add_media_files_and_posts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "posts",
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("posts", "scheduled_at")
