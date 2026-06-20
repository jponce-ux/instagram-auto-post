"""add processing_started_at to posts table

Revision ID: add_processing_started_at
Revises: add_username_is_active_to_instagram
Create Date: 2026-06-19 22:05:26

Adds processing_started_at column to track when a post entered
processing or retrying state, for stalled post timeout detection.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_processing_started_at"
down_revision = "add_username_is_active_ig"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "posts",
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("posts", "processing_started_at")
