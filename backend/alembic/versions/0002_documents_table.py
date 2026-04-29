"""documents table

Revision ID: 0002_documents
Revises: 0001_users
Create Date: 2026-04-28

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_documents"
down_revision: Union[str, None] = "0001_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("doc_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="queued"),
        # file metadata + dedup
        sa.Column("file_name", sa.String(length=512), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.CHAR(length=64), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=False),
        # denormalized columns for fast queries
        sa.Column("ay", sa.String(length=16), nullable=True),
        sa.Column("fy", sa.String(length=16), nullable=True),
        sa.Column("employer_name", sa.String(length=256), nullable=True),
        sa.Column("employer_tan", sa.String(length=32), nullable=True),
        sa.Column("employee_pan", sa.String(length=16), nullable=True),
        sa.Column("gross_salary", sa.Numeric(15, 2), nullable=True),
        sa.Column("total_tds", sa.Numeric(15, 2), nullable=True),
        sa.Column("taxable_income", sa.Numeric(15, 2), nullable=True),
        sa.Column("tax_payable", sa.Numeric(15, 2), nullable=True),
        sa.Column("regime", sa.String(length=8), nullable=True),
        # extracted truth + audit
        sa.Column("parsed_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("confidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("parser_provider", sa.String(length=32), nullable=True),
        sa.Column("parser_model", sa.String(length=64), nullable=True),
        sa.Column("parser_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.UniqueConstraint("user_id", "sha256", name="uq_documents_user_sha256"),
    )
    op.create_index("ix_documents_user_id", "documents", ["user_id"])
    op.create_index("ix_documents_user_status", "documents", ["user_id", "status"])
    op.create_index("ix_documents_user_doc_type", "documents", ["user_id", "doc_type"])


def downgrade() -> None:
    op.drop_index("ix_documents_user_doc_type", table_name="documents")
    op.drop_index("ix_documents_user_status", table_name="documents")
    op.drop_index("ix_documents_user_id", table_name="documents")
    op.drop_table("documents")
