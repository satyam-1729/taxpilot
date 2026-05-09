"""[OBSOLETE — applied 2026-05-08, retained for historical reference]

After migration 0008 dropped the plaintext / legacy-Fernet columns, this script
no longer runs (the columns it reads from are gone). It is kept in the tree so
operators can see how the original backfill happened. Do NOT attempt to re-run.

────────────────────────────────────────────────────────────────────────────────

Stage 2 backfill: populate the new ciphertext columns from existing plaintext.

Background
──────────
Migration 0007 added nullable ciphertext columns alongside the existing plaintext
ones. The app dual-writes from now on, so any *new* row already has both forms
populated. This script walks every *old* row and fills the ciphertext side from
the plaintext side, so by the time Stage 3 flips reads to ciphertext, every row
is decrypt-able.

What we backfill
────────────────
  users:
    - mint dek_wrapped if NULL
    - email_ct + email_bidx        from users.email
    - phone_ct + phone_bidx        from users.phone
    - name_ct                      from users.name
    - dob_ct                       from users.dob
    - pan_ct                       from users.pan_encrypted (legacy Fernet → DEK AES-GCM)

  bank_accounts:
    - account_number_ct            from bank_accounts.account_number_encrypted (legacy → DEK)

  documents:
    - parsed_json_ct + every *_ct  from the matching plaintext column

Things we cannot backfill
─────────────────────────
  - aadhaar_ct: we never stored the full Aadhaar, only aadhaar_last4. Old rows
    will pick this up on the user's next KYC submission. Not an error.

Properties
──────────
  - **Idempotent**: rows that already have *_ct populated are skipped.
  - **Per-user transactional**: each user's row + their bank accounts + their
    documents are committed in one transaction. A crash mid-run loses at most
    the user currently being processed.
  - **Resilient**: a corrupt legacy ciphertext (e.g., Fernet decrypt fails)
    is logged and the row is skipped. The rest of the user's data still
    backfills. Counts are reported at the end so an operator can investigate.

Usage
─────
    cd backend && source .venv/bin/activate
    python scripts/backfill_envelope.py [--dry-run] [--user-id UUID]

  --dry-run    Walks everything, reports what would change, commits nothing.
  --user-id    Only process this single user. Useful for re-running after a fix.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID

# Make `import app` work when invoked as `python scripts/backfill_envelope.py`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models import BankAccount, Document, User  # noqa: E402
from app.utils.crypto import (  # noqa: E402
    blind_index,
    decrypt_field,
    encrypt_date,
    encrypt_decimal,
    encrypt_json,
    encrypt_str,
    generate_dek,
    unwrap_dek,
    wrap_dek,
)

logger = logging.getLogger("backfill")


# ─────────────────────────────────────────────────────────────────────────────
# Counters
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Stats:
    users_seen: int = 0
    users_dek_minted: int = 0
    user_fields_encrypted: int = 0
    user_fields_skipped: int = 0
    bank_accounts_seen: int = 0
    bank_accounts_encrypted: int = 0
    bank_accounts_skipped: int = 0
    bank_accounts_failed: int = 0
    documents_seen: int = 0
    documents_encrypted: int = 0
    documents_skipped: int = 0
    errors: list[str] = field(default_factory=list)

    def report(self) -> str:
        out = [
            "─── Backfill Report ──────────────────────────────────────────",
            f"  users seen ............... {self.users_seen}",
            f"  users with new DEK ....... {self.users_dek_minted}",
            f"  user fields encrypted .... {self.user_fields_encrypted}",
            f"  user fields skipped ...... {self.user_fields_skipped} (already had _ct)",
            f"  bank accounts seen ....... {self.bank_accounts_seen}",
            f"  bank accounts encrypted .. {self.bank_accounts_encrypted}",
            f"  bank accounts skipped .... {self.bank_accounts_skipped}",
            f"  bank accounts failed ..... {self.bank_accounts_failed}",
            f"  documents seen ........... {self.documents_seen}",
            f"  documents encrypted ...... {self.documents_encrypted}",
            f"  documents skipped ........ {self.documents_skipped}",
        ]
        if self.errors:
            out.append("")
            out.append(f"  errors ({len(self.errors)}):")
            for e in self.errors[:20]:
                out.append(f"    - {e}")
            if len(self.errors) > 20:
                out.append(f"    … and {len(self.errors) - 20} more")
        out.append("──────────────────────────────────────────────────────────────")
        return "\n".join(out)


# ─────────────────────────────────────────────────────────────────────────────
# Per-user backfill
# ─────────────────────────────────────────────────────────────────────────────

async def backfill_user(session, user: User, stats: Stats, dry_run: bool) -> bytes:
    """Mint+wrap DEK if missing, encrypt PII fields. Returns the unwrapped DEK."""

    if user.dek_wrapped is None:
        dek = generate_dek()
        if not dry_run:
            user.dek_wrapped = wrap_dek(dek)
        stats.users_dek_minted += 1
    else:
        dek = unwrap_dek(user.dek_wrapped)

    # Pairs of (predicate, action). Predicate decides if we encrypt; action does it.
    if user.email:
        if user.email_ct is None:
            if not dry_run:
                user.email_ct = encrypt_str(dek, user.email)
                user.email_bidx = blind_index(user.email)
            stats.user_fields_encrypted += 1
        else:
            stats.user_fields_skipped += 1

    if user.phone:
        if user.phone_ct is None:
            if not dry_run:
                user.phone_ct = encrypt_str(dek, user.phone)
                user.phone_bidx = blind_index(user.phone)
            stats.user_fields_encrypted += 1
        else:
            stats.user_fields_skipped += 1

    if user.name:
        if user.name_ct is None:
            if not dry_run:
                user.name_ct = encrypt_str(dek, user.name)
            stats.user_fields_encrypted += 1
        else:
            stats.user_fields_skipped += 1

    if user.dob:
        if user.dob_ct is None:
            if not dry_run:
                user.dob_ct = encrypt_date(dek, user.dob)
            stats.user_fields_encrypted += 1
        else:
            stats.user_fields_skipped += 1

    # Legacy Fernet PAN → DEK AES-GCM mirror.
    if user.pan_encrypted and user.pan_ct is None:
        try:
            pan_plain = decrypt_field(user.pan_encrypted)
            if not dry_run:
                user.pan_ct = encrypt_str(dek, pan_plain)
            stats.user_fields_encrypted += 1
        except ValueError as e:
            stats.errors.append(f"user {user.id} pan_encrypted: {e}")

    return dek


async def backfill_bank_accounts(session, user: User, dek: bytes, stats: Stats, dry_run: bool) -> None:
    rows = (await session.execute(
        select(BankAccount).where(BankAccount.user_id == user.id)
    )).scalars().all()
    for row in rows:
        stats.bank_accounts_seen += 1
        if row.account_number_ct is not None:
            stats.bank_accounts_skipped += 1
            continue
        try:
            plain = decrypt_field(row.account_number_encrypted)
            if not dry_run:
                row.account_number_ct = encrypt_str(dek, plain)
            stats.bank_accounts_encrypted += 1
        except ValueError as e:
            stats.bank_accounts_failed += 1
            stats.errors.append(f"bank_account {row.id}: legacy Fernet decrypt failed: {e}")


async def backfill_documents(session, user: User, dek: bytes, stats: Stats, dry_run: bool) -> None:
    rows = (await session.execute(
        select(Document).where(Document.user_id == user.id)
    )).scalars().all()
    for row in rows:
        stats.documents_seen += 1
        # parsed_json_ct is the canonical "is this row backfilled" signal — if
        # it's set we trust everything else got mirrored at write-time too.
        if row.parsed_json_ct is not None:
            stats.documents_skipped += 1
            continue

        if not dry_run:
            if row.parsed_json is not None:
                row.parsed_json_ct = encrypt_json(dek, row.parsed_json)
            if row.employer_name:
                row.employer_name_ct = encrypt_str(dek, row.employer_name)
            if row.employer_tan:
                row.employer_tan_ct = encrypt_str(dek, row.employer_tan)
            if row.employee_pan:
                row.employee_pan_ct = encrypt_str(dek, row.employee_pan)
            if row.gross_salary is not None:
                row.gross_salary_ct = encrypt_decimal(dek, row.gross_salary)
            if row.total_tds is not None:
                row.total_tds_ct = encrypt_decimal(dek, row.total_tds)
            if row.taxable_income is not None:
                row.taxable_income_ct = encrypt_decimal(dek, row.taxable_income)
            if row.tax_payable is not None:
                row.tax_payable_ct = encrypt_decimal(dek, row.tax_payable)
            if row.stcg_111a is not None:
                row.stcg_111a_ct = encrypt_decimal(dek, row.stcg_111a)
            if row.stcg_non_equity is not None:
                row.stcg_non_equity_ct = encrypt_decimal(dek, row.stcg_non_equity)
            if row.ltcg_112a is not None:
                row.ltcg_112a_ct = encrypt_decimal(dek, row.ltcg_112a)
            if row.ltcg_non_equity is not None:
                row.ltcg_non_equity_ct = encrypt_decimal(dek, row.ltcg_non_equity)
            if row.dividends_total is not None:
                row.dividends_total_ct = encrypt_decimal(dek, row.dividends_total)
            if row.exempt_income_total is not None:
                row.exempt_income_total_ct = encrypt_decimal(dek, row.exempt_income_total)
            if row.total_invested is not None:
                row.total_invested_ct = encrypt_decimal(dek, row.total_invested)
        stats.documents_encrypted += 1


# ─────────────────────────────────────────────────────────────────────────────
# Driver
# ─────────────────────────────────────────────────────────────────────────────

async def run(dry_run: bool, user_id: UUID | None) -> Stats:
    stats = Stats()

    # First pass: just collect the user IDs. We use a fresh session per user
    # below so a rollback on user N doesn't expire ORM state for user N+1.
    async with SessionLocal() as session:
        query = select(User.id)
        if user_id is not None:
            query = query.where(User.id == user_id)
        user_ids = [row[0] for row in (await session.execute(query)).all()]

    for uid in user_ids:
        stats.users_seen += 1
        async with SessionLocal() as session:
            try:
                user = await session.get(User, uid)
                if user is None:
                    continue
                dek = await backfill_user(session, user, stats, dry_run)
                await backfill_bank_accounts(session, user, dek, stats, dry_run)
                await backfill_documents(session, user, dek, stats, dry_run)
                if dry_run:
                    await session.rollback()
                else:
                    await session.commit()
                logger.info("user %s done", uid)
            except Exception as e:  # noqa: BLE001  - log + continue, don't abort the whole run
                logger.exception("user %s failed", uid)
                stats.errors.append(f"user {uid}: {e!r}")
                await session.rollback()

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage 2 envelope-encryption backfill.")
    parser.add_argument("--dry-run", action="store_true", help="Walk everything, commit nothing.")
    parser.add_argument("--user-id", type=UUID, default=None, help="Backfill a single user only.")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    if args.dry_run:
        logger.info("DRY RUN — no changes will be committed.")
    if args.user_id:
        logger.info("Targeting single user %s", args.user_id)

    stats = asyncio.run(run(dry_run=args.dry_run, user_id=args.user_id))
    print("\n" + stats.report())
    return 1 if stats.errors else 0


if __name__ == "__main__":
    sys.exit(main())
