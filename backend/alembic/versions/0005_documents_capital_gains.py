"""documents: capital gains denormalized columns + broker

Revision ID: 0005_docs_cg
Revises: 0004_bank_accounts
Create Date: 2026-05-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_docs_cg"
down_revision: Union[str, None] = "0004_bank_accounts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("broker", sa.String(length=64), nullable=True))
    op.add_column("documents", sa.Column("stcg_111a", sa.Numeric(15, 2), nullable=True))
    op.add_column("documents", sa.Column("stcg_non_equity", sa.Numeric(15, 2), nullable=True))
    op.add_column("documents", sa.Column("ltcg_112a", sa.Numeric(15, 2), nullable=True))
    op.add_column("documents", sa.Column("ltcg_non_equity", sa.Numeric(15, 2), nullable=True))
    op.add_column("documents", sa.Column("dividends_total", sa.Numeric(15, 2), nullable=True))
    op.add_column("documents", sa.Column("exempt_income_total", sa.Numeric(15, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "exempt_income_total")
    op.drop_column("documents", "dividends_total")
    op.drop_column("documents", "ltcg_non_equity")
    op.drop_column("documents", "ltcg_112a")
    op.drop_column("documents", "stcg_non_equity")
    op.drop_column("documents", "stcg_111a")
    op.drop_column("documents", "broker")
