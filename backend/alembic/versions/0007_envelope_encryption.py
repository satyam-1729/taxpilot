"""envelope encryption: add dek_wrapped + ciphertext + blind-index columns

Revision ID: 0007_envelope
Revises: 0006_invested
Create Date: 2026-05-07

This migration is **purely additive**. We add nullable columns alongside the
existing plaintext / Fernet columns. The application then dual-writes (plaintext
+ ciphertext) until every row is backfilled, after which a follow-up migration
will drop the plaintext columns. Until then nothing breaks for existing rows.

Columns added:

  users:
    - dek_wrapped       BYTEA  ← wrapped per-user DEK
    - email_ct          BYTEA
    - email_bidx        BYTEA  ← HMAC for WHERE email_bidx=? lookups
    - phone_ct          BYTEA
    - phone_bidx        BYTEA  ← HMAC for OTP-by-phone lookups
    - name_ct           BYTEA
    - dob_ct            BYTEA
    - pan_ct            BYTEA  ← AES-GCM under DEK (replaces pan_encrypted)
    - aadhaar_ct        BYTEA  ← future: full Aadhaar (was last4-only)

  bank_accounts:
    - account_number_ct BYTEA  ← AES-GCM under DEK (replaces account_number_encrypted)

  documents:
    - parsed_json_ct    BYTEA  ← whole parsed_json blob, encrypted
    - employer_name_ct  BYTEA
    - employer_tan_ct   BYTEA
    - employee_pan_ct   BYTEA
    - gross_salary_ct   BYTEA
    - total_tds_ct      BYTEA
    - taxable_income_ct BYTEA
    - tax_payable_ct    BYTEA
    - stcg_111a_ct      BYTEA
    - stcg_non_equity_ct BYTEA
    - ltcg_112a_ct      BYTEA
    - ltcg_non_equity_ct BYTEA
    - dividends_total_ct BYTEA
    - exempt_income_total_ct BYTEA
    - total_invested_ct BYTEA
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_envelope"
down_revision: Union[str, None] = "0006_invested"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ────────────────────────────────────────────────────────────────
    op.add_column("users", sa.Column("dek_wrapped", sa.LargeBinary(), nullable=True))
    op.add_column("users", sa.Column("email_ct", sa.LargeBinary(), nullable=True))
    op.add_column("users", sa.Column("email_bidx", sa.LargeBinary(), nullable=True))
    op.add_column("users", sa.Column("phone_ct", sa.LargeBinary(), nullable=True))
    op.add_column("users", sa.Column("phone_bidx", sa.LargeBinary(), nullable=True))
    op.add_column("users", sa.Column("name_ct", sa.LargeBinary(), nullable=True))
    op.add_column("users", sa.Column("dob_ct", sa.LargeBinary(), nullable=True))
    op.add_column("users", sa.Column("pan_ct", sa.LargeBinary(), nullable=True))
    op.add_column("users", sa.Column("aadhaar_ct", sa.LargeBinary(), nullable=True))

    op.create_index("ix_users_email_bidx", "users", ["email_bidx"])
    op.create_index("ix_users_phone_bidx", "users", ["phone_bidx"])

    # ── bank_accounts ────────────────────────────────────────────────────────
    op.add_column("bank_accounts", sa.Column("account_number_ct", sa.LargeBinary(), nullable=True))

    # ── documents ────────────────────────────────────────────────────────────
    op.add_column("documents", sa.Column("parsed_json_ct", sa.LargeBinary(), nullable=True))
    op.add_column("documents", sa.Column("employer_name_ct", sa.LargeBinary(), nullable=True))
    op.add_column("documents", sa.Column("employer_tan_ct", sa.LargeBinary(), nullable=True))
    op.add_column("documents", sa.Column("employee_pan_ct", sa.LargeBinary(), nullable=True))
    op.add_column("documents", sa.Column("gross_salary_ct", sa.LargeBinary(), nullable=True))
    op.add_column("documents", sa.Column("total_tds_ct", sa.LargeBinary(), nullable=True))
    op.add_column("documents", sa.Column("taxable_income_ct", sa.LargeBinary(), nullable=True))
    op.add_column("documents", sa.Column("tax_payable_ct", sa.LargeBinary(), nullable=True))
    op.add_column("documents", sa.Column("stcg_111a_ct", sa.LargeBinary(), nullable=True))
    op.add_column("documents", sa.Column("stcg_non_equity_ct", sa.LargeBinary(), nullable=True))
    op.add_column("documents", sa.Column("ltcg_112a_ct", sa.LargeBinary(), nullable=True))
    op.add_column("documents", sa.Column("ltcg_non_equity_ct", sa.LargeBinary(), nullable=True))
    op.add_column("documents", sa.Column("dividends_total_ct", sa.LargeBinary(), nullable=True))
    op.add_column("documents", sa.Column("exempt_income_total_ct", sa.LargeBinary(), nullable=True))
    op.add_column("documents", sa.Column("total_invested_ct", sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    # documents
    for col in (
        "total_invested_ct",
        "exempt_income_total_ct",
        "dividends_total_ct",
        "ltcg_non_equity_ct",
        "ltcg_112a_ct",
        "stcg_non_equity_ct",
        "stcg_111a_ct",
        "tax_payable_ct",
        "taxable_income_ct",
        "total_tds_ct",
        "gross_salary_ct",
        "employee_pan_ct",
        "employer_tan_ct",
        "employer_name_ct",
        "parsed_json_ct",
    ):
        op.drop_column("documents", col)

    # bank_accounts
    op.drop_column("bank_accounts", "account_number_ct")

    # users
    op.drop_index("ix_users_phone_bidx", table_name="users")
    op.drop_index("ix_users_email_bidx", table_name="users")
    for col in (
        "aadhaar_ct",
        "pan_ct",
        "dob_ct",
        "name_ct",
        "phone_bidx",
        "phone_ct",
        "email_bidx",
        "email_ct",
        "dek_wrapped",
    ):
        op.drop_column("users", col)
