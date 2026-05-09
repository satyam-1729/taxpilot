"""drop plaintext PII columns now that ciphertext is the source of truth

Revision ID: 0008_drop_pt
Revises: 0007_envelope
Create Date: 2026-05-09

After Stage 3 read flip + Stage 2 backfill, every row's encrypted *_ct mirror
is up to date. Stage 4 drops the plaintext columns and the legacy Fernet
columns, leaving ciphertext as the only source of truth.

Columns dropped:

  users:
    - email                ← lookup is now via email_bidx
    - phone                ← lookup is now via phone_bidx
    - name
    - dob
    - pan_encrypted        ← legacy Fernet, replaced by pan_ct (DEK AES-GCM)

  bank_accounts:
    - account_number_encrypted   ← legacy Fernet, replaced by account_number_ct

  documents:
    - parsed_json
    - employer_name
    - employer_tan
    - employee_pan
    - gross_salary
    - total_tds
    - taxable_income
    - tax_payable
    - stcg_111a / stcg_non_equity
    - ltcg_112a / ltcg_non_equity
    - dividends_total
    - exempt_income_total
    - total_invested

Kept plaintext (not PII or required for filtering / lookup):
    - users.firebase_uid, pan_last4, aadhaar_last4, verified, verified_at, …
    - documents.doc_type, status, ay, fy, regime, broker, file_name, sha256, …
    - bank_accounts.bank_name, ifsc, account_last4, account_type, is_primary, …

This migration is **destructive**. Backups taken before 0008 still contain
plaintext; new backups won't. Roll-back is not possible without restoring
from a pre-0008 dump.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0008_drop_pt"
down_revision: Union[str, None] = "0007_envelope"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ────────────────────────────────────────────────────────────────
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_phone", table_name="users")
    op.drop_column("users", "email")
    op.drop_column("users", "phone")
    op.drop_column("users", "name")
    op.drop_column("users", "dob")
    op.drop_column("users", "pan_encrypted")

    # ── bank_accounts ────────────────────────────────────────────────────────
    # Make account_number_ct NOT NULL — every row was backfilled in Stage 2.
    op.alter_column("bank_accounts", "account_number_ct", nullable=False)
    op.drop_column("bank_accounts", "account_number_encrypted")

    # ── documents ────────────────────────────────────────────────────────────
    for col in (
        "parsed_json",
        "employer_name",
        "employer_tan",
        "employee_pan",
        "gross_salary",
        "total_tds",
        "taxable_income",
        "tax_payable",
        "stcg_111a",
        "stcg_non_equity",
        "ltcg_112a",
        "ltcg_non_equity",
        "dividends_total",
        "exempt_income_total",
        "total_invested",
    ):
        op.drop_column("documents", col)


def downgrade() -> None:
    # Plaintext data is gone — downgrade restores empty columns. Useful for
    # local dev rollbacks; production must restore from backup.

    # users
    op.add_column("users", sa.Column("pan_encrypted", sa.LargeBinary(), nullable=True))
    op.add_column("users", sa.Column("dob", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("name", sa.String(length=200), nullable=True))
    op.add_column("users", sa.Column("phone", sa.String(length=32), nullable=True))
    op.add_column("users", sa.Column("email", sa.String(length=320), nullable=True))
    op.create_index("ix_users_phone", "users", ["phone"])
    op.create_index("ix_users_email", "users", ["email"])

    # bank_accounts
    op.add_column(
        "bank_accounts",
        sa.Column("account_number_encrypted", sa.LargeBinary(), nullable=True),
    )
    op.alter_column("bank_accounts", "account_number_ct", nullable=True)

    # documents
    op.add_column("documents", sa.Column("total_invested", sa.Numeric(15, 2), nullable=True))
    op.add_column("documents", sa.Column("exempt_income_total", sa.Numeric(15, 2), nullable=True))
    op.add_column("documents", sa.Column("dividends_total", sa.Numeric(15, 2), nullable=True))
    op.add_column("documents", sa.Column("ltcg_non_equity", sa.Numeric(15, 2), nullable=True))
    op.add_column("documents", sa.Column("ltcg_112a", sa.Numeric(15, 2), nullable=True))
    op.add_column("documents", sa.Column("stcg_non_equity", sa.Numeric(15, 2), nullable=True))
    op.add_column("documents", sa.Column("stcg_111a", sa.Numeric(15, 2), nullable=True))
    op.add_column("documents", sa.Column("tax_payable", sa.Numeric(15, 2), nullable=True))
    op.add_column("documents", sa.Column("taxable_income", sa.Numeric(15, 2), nullable=True))
    op.add_column("documents", sa.Column("total_tds", sa.Numeric(15, 2), nullable=True))
    op.add_column("documents", sa.Column("gross_salary", sa.Numeric(15, 2), nullable=True))
    op.add_column("documents", sa.Column("employee_pan", sa.String(length=16), nullable=True))
    op.add_column("documents", sa.Column("employer_tan", sa.String(length=32), nullable=True))
    op.add_column("documents", sa.Column("employer_name", sa.String(length=256), nullable=True))
    op.add_column("documents", sa.Column("parsed_json", JSONB(), nullable=True))
