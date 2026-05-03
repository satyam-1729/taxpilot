"""bank_accounts table

Revision ID: 0004_bank_accounts
Revises: 0003_users_dob
Create Date: 2026-05-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_bank_accounts"
down_revision: Union[str, None] = "0003_users_dob"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bank_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("account_number_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("account_last4", sa.CHAR(length=4), nullable=False),
        sa.Column("ifsc", sa.String(length=11), nullable=False),
        sa.Column("bank_name", sa.String(length=120), nullable=False),
        sa.Column("account_type", sa.String(length=16), nullable=False, server_default="savings"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_bank_accounts_user_id", "bank_accounts", ["user_id"])

    # Only one primary bank account per user, enforced at DB level.
    op.create_index(
        "uq_bank_accounts_one_primary_per_user",
        "bank_accounts",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_primary = true"),
    )


def downgrade() -> None:
    op.drop_index("uq_bank_accounts_one_primary_per_user", table_name="bank_accounts")
    op.drop_index("ix_bank_accounts_user_id", table_name="bank_accounts")
    op.drop_table("bank_accounts")
