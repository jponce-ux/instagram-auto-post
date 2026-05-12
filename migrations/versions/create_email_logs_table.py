"""create_email_logs_table

Revision ID: create_email_logs_table
Revises: add_scheduled_at_to_posts
Create Date: 2026-05-12

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "create_email_logs_table"
down_revision: Union[str, None] = "add_scheduled_at_to_posts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "email_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("email_type", sa.String(50), nullable=False),
        sa.Column("to_email", sa.String(255), nullable=False),
        sa.Column("from_email", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("message_id", sa.String(255), nullable=True),
        sa.Column("template_name", sa.String(100), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Indexes
    op.create_index("ix_email_logs_id", "email_logs", ["id"])
    op.create_index("ix_email_logs_user_id", "email_logs", ["user_id"])
    op.create_index("ix_email_logs_email_type", "email_logs", ["email_type"])
    op.create_index("ix_email_logs_status", "email_logs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_email_logs_status", table_name="email_logs")
    op.drop_index("ix_email_logs_email_type", table_name="email_logs")
    op.drop_index("ix_email_logs_user_id", table_name="email_logs")
    op.drop_index("ix_email_logs_id", table_name="email_logs")
    op.drop_table("email_logs")
