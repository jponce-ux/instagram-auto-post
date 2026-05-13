"""add username and is_active to instagram_accounts

Revision ID: add_username_is_active_ig
Revises: add_is_verified_to_users
Create Date: 2026-05-13

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "add_username_is_active_ig"
down_revision: Union[str, None] = "387251a18678"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("instagram_accounts", sa.Column("username", sa.String(), nullable=True))
    op.add_column("instagram_accounts", sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False))


def downgrade() -> None:
    op.drop_column("instagram_accounts", "is_active")
    op.drop_column("instagram_accounts", "username")