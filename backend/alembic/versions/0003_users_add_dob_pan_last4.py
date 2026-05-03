"""users: add dob + pan_last4; reset verification for existing rows

Revision ID: 0003_users_dob
Revises: 0002_documents
Create Date: 2026-04-29

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_users_dob"
down_revision: Union[str, None] = "0002_documents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("dob", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("pan_last4", sa.CHAR(length=4), nullable=True))

    # Reset existing verified rows so they re-run KYC with the new required fields.
    op.execute(
        """
        UPDATE users
        SET verified = false,
            verified_at = NULL
        WHERE verified = true
          AND (dob IS NULL OR pan_last4 IS NULL)
        """
    )


def downgrade() -> None:
    op.drop_column("users", "pan_last4")
    op.drop_column("users", "dob")
