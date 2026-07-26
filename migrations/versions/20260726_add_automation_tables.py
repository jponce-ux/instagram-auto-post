"""add automation tables (hashtag_collections, content_templates, recurring_schedules)

Revision ID: add_automation_tables
Revises: add_processing_started_at, add_media_file_table, add_retrying_post_status, add_thumbnail_key_to_media_files
Create Date: 2026-07-26

Creates three new tables for automation tools:
- hashtag_collections: reusable hashtag collections
- content_templates: caption templates with placeholder support
- recurring_schedules: auto-post scheduling
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_automation_tables"
down_revision: Union[str, None] = "add_processing_started_at"  # Multi-head: bases on one head
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create hashtag_collections table
    op.create_table(
        "hashtag_collections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("hashtags", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_hashtag_collections_id", "hashtag_collections", ["id"], unique=False
    )
    op.create_index(
        "ix_hashtag_collections_user_id", "hashtag_collections", ["user_id"], unique=False
    )

    # Create content_templates table
    op.create_table(
        "content_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("caption_template", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_content_templates_id", "content_templates", ["id"], unique=False
    )
    op.create_index(
        "ix_content_templates_user_id", "content_templates", ["user_id"], unique=False
    )

    # Create recurring_schedules table
    op.create_table(
        "recurring_schedules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("ig_account_id", sa.Integer(), nullable=False),
        sa.Column("frequency", sa.String(length=20), nullable=False),
        sa.Column("time_of_day", sa.Time(), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=True),
        sa.Column("template_id", sa.Integer(), nullable=True),
        sa.Column("hashtag_collection_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["ig_account_id"], ["instagram_accounts.id"]),
        sa.ForeignKeyConstraint(["template_id"], ["content_templates.id"]),
        sa.ForeignKeyConstraint(["hashtag_collection_id"], ["hashtag_collections.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_recurring_schedules_id", "recurring_schedules", ["id"], unique=False
    )
    op.create_index(
        "ix_recurring_schedules_user_id",
        "recurring_schedules",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_recurring_schedules_ig_account_id",
        "recurring_schedules",
        ["ig_account_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_recurring_schedules_ig_account_id", "recurring_schedules")
    op.drop_index("ix_recurring_schedules_user_id", "recurring_schedules")
    op.drop_index("ix_recurring_schedules_id", "recurring_schedules")
    op.drop_table("recurring_schedules")

    op.drop_index("ix_content_templates_user_id", "content_templates")
    op.drop_index("ix_content_templates_id", "content_templates")
    op.drop_table("content_templates")

    op.drop_index("ix_hashtag_collections_user_id", "hashtag_collections")
    op.drop_index("ix_hashtag_collections_id", "hashtag_collections")
    op.drop_table("hashtag_collections")
