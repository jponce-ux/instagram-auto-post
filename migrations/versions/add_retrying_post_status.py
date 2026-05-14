"""add retrying post status

Revision ID: add_retrying_post_status
Revises: create_email_logs_table
Create Date: 2026-05-13

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_retrying_post_status"
down_revision: Union[str, None] = "create_email_logs_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE poststatus ADD VALUE IF NOT EXISTS 'retrying'")


def downgrade() -> None:
    op.execute("DELETE FROM posts WHERE status = 'retrying'")
    op.execute("ALTER TYPE poststatus RENAME TO poststatus_old")
    op.execute(
        "CREATE TYPE poststatus AS ENUM ('pending', 'processing', 'published', 'failed')"
    )
    op.execute(
        "ALTER TABLE posts ALTER COLUMN status TYPE poststatus USING status::text::poststatus"
    )
    op.execute("DROP TYPE poststatus_old")