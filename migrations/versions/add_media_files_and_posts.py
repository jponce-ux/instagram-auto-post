"""add_media_files_and_posts

Revision ID: add_media_files_and_posts
Revises: add_instagram_account
Create Date: 2026-04-05

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "add_media_files_and_posts"
down_revision: Union[str, None] = "add_instagram_account"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create media_files table
    op.create_table(
        "media_files",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("original_filename", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
        sa.Index("ix_media_files_id", "id"),
    )

    # Create posts table
    op.create_table(
        "posts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("ig_account_id", sa.Integer(), nullable=False),
        sa.Column("media_file_id", sa.Integer(), nullable=False),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("pending", "processing", "published", "failed", name="poststatus"),
            nullable=False,
        ),
        sa.Column("ig_container_id", sa.String(), nullable=True),
        sa.Column("ig_media_id", sa.String(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["ig_account_id"],
            ["instagram_accounts.id"],
        ),
        sa.ForeignKeyConstraint(
            ["media_file_id"],
            ["media_files.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_posts_id", "id"),
    )


def downgrade() -> None:
    op.drop_index("ix_posts_id", table_name="posts")
    op.drop_table("posts")
    op.drop_index("ix_media_files_id", table_name="media_files")
    op.drop_table("media_files")
    op.execute("DROP TYPE IF EXISTS poststatus")
