"""add scheduled post status

Merge point for the multi-head migration graph plus the new 'scheduled'
Postgres enum value. Depends on all previous heads so that upgrading to
this revision converges the branch graph into a single head.

Revision ID: add_scheduled_post_status
Revises: add_automation_tables, add_media_file_table, add_retrying_post_status, add_thumbnail_key_to_media_files
Create Date: 2026-08-05

"""

from typing import Sequence, Union

from alembic import op


revision: str = "add_scheduled_post_status"
down_revision: Union[str, Sequence[str], None] = (
    "add_automation_tables",
    "add_media_file_table",
    "add_retrying_post_status",
    "add_thumbnail_key_to_media_files",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE poststatus ADD VALUE IF NOT EXISTS 'scheduled'")


def downgrade() -> None:
    op.execute("DELETE FROM posts WHERE status = 'scheduled'")
    op.execute("ALTER TYPE poststatus RENAME TO poststatus_old")
    op.execute(
        "CREATE TYPE poststatus AS ENUM "
        "('pending', 'processing', 'published', 'failed', 'retrying')"
    )
    op.execute(
        "ALTER TABLE posts ALTER COLUMN status TYPE poststatus "
        "USING status::text::poststatus"
    )
    op.execute("DROP TYPE poststatus_old")