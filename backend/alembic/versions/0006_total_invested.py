"""documents: add total_invested column

Revision ID: 0006_invested
Revises: 0005_docs_cg
Create Date: 2026-05-04

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_invested"
down_revision: Union[str, None] = "0005_docs_cg"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("total_invested", sa.Numeric(15, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "total_invested")
