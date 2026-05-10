"""Documents API: upload tax documents, list parsed results.

Upload flow:
  1. Compute sha256, dedup against (user_id, sha256). Re-uploading the same file
     returns the cached row — no Anthropic call.
  2. If the PDF is unencrypted, classify it (form16 / capital_gains). Reject
     with 422 if we can't tell what it is.
  3. If the PDF is encrypted, store with status='needs_password'. Classification
     happens after the user supplies the password.
  4. Parsing is dispatched by doc_type to the matching extractor. Form 16 →
     parse_form16; capital gains → parse_capital_gains.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import current_user, get_user_dek
from app.db.session import SessionLocal, get_db
from app.models import Document, User
from app.schemas.document import DocumentOut, UploadResponse, document_out_from
from app.services.parser.ais import (
    AisParserConfigError,
    AisParserError,
    denorm_ais,
    parse_ais,
)
from app.services.parser.capital_gains import (
    CapitalGainsParserError,
    denorm_capital_gains,
    parse_capital_gains_pdf,
    parse_capital_gains_xlsx,
)
from app.services.parser.classifier import DocType, classify
from app.services.parser.form16 import ParserConfigError, ParserError, parse_form16
from app.services.parser.pdf import decrypt_pdf, is_encrypted
from app.services.parser.xlsx import is_xlsx, xlsx_to_text
from app.utils.crypto import (
    encrypt_decimal,
    encrypt_json,
    encrypt_str,
    unwrap_dek,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])

KNOWN_DOC_TYPES: set[DocType] = {"form16", "capital_gains", "ais"}
MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15 MB
UNKNOWN_DOC_DETAIL = (
    "We couldn't recognise this document. Supported: Form 16 (TDS certificate, PDF), "
    "AIS / TIS / Form 26AS (PDF from incometax.gov.in), "
    "or a capital gains / broker P&L statement (Zerodha, Groww, Upstox, etc. — XLSX) "
    "or a CAMS / KFinTech CAS (PDF). For PDFs, make sure they're text-based not scanned images."
)
ACCEPTED_MIME = {
    "application/pdf",
    "application/octet-stream",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # xlsx
    "application/vnd.ms-excel",
}


def _uploads_root() -> Path:
    return Path(get_settings().uploads_dir).resolve()


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> UploadResponse:
    if file.content_type not in ACCEPTED_MIME:
        raise HTTPException(
            status_code=415,
            detail=f"Expected a PDF or XLSX, got {file.content_type}",
        )

    body = await file.read()
    if len(body) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(body) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (>{MAX_UPLOAD_BYTES // 1024 // 1024} MB)",
        )

    sha256 = hashlib.sha256(body).hexdigest()

    # Dedup: same user + same sha256 → return existing row, no parse re-run
    existing = await db.execute(
        select(Document).where(Document.user_id == user.id, Document.sha256 == sha256)
    )
    existing_row = existing.scalar_one_or_none()
    if existing_row is not None:
        return UploadResponse(id=existing_row.id, status=existing_row.status, deduplicated=True)

    # XLSX files aren't password-protected by brokers; only PDFs need the encryption check.
    is_xlsx_file = is_xlsx(body)
    encrypted = False
    if not is_xlsx_file:
        try:
            encrypted = is_encrypted(body)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    # If unencrypted (or XLSX), classify now and reject unknown docs before saving.
    detected: DocType | None = None
    if not encrypted:
        detected = classify(body)
        if detected == "unknown":
            raise HTTPException(status_code=422, detail=UNKNOWN_DOC_DETAIL)

    doc_id = uuid4()
    user_dir = _uploads_root() / str(user.id)
    user_dir.mkdir(parents=True, exist_ok=True)
    extension = "xlsx" if is_xlsx_file else "pdf"
    target = user_dir / f"{doc_id}.{extension}"
    target.write_bytes(body)

    initial_status = "needs_password" if encrypted else "queued"

    row = Document(
        id=doc_id,
        user_id=user.id,
        doc_type=detected or "unknown",
        status=initial_status,
        file_name=file.filename or f"tax-document.{extension}",
        file_size_bytes=len(body),
        sha256=sha256,
        storage_path=str(target),
    )
    db.add(row)
    await db.commit()

    if not encrypted:
        background_tasks.add_task(_parse_in_background, doc_id)

    return UploadResponse(id=doc_id, status=initial_status, deduplicated=False)


class DecryptRequest(BaseModel):
    password: str


@router.post("/{doc_id}/decrypt", response_model=UploadResponse)
async def submit_password(
    doc_id: UUID,
    body: DecryptRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> UploadResponse:
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.user_id == user.id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if row.status not in {"needs_password", "failed"}:
        raise HTTPException(
            status_code=400,
            detail=f"Document is not awaiting a password (status={row.status})",
        )

    encrypted_bytes = Path(row.storage_path).read_bytes()
    try:
        decrypted = decrypt_pdf(encrypted_bytes, body.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Classify the now-readable PDF; reject unknown.
    detected = classify(decrypted)
    if detected == "unknown":
        raise HTTPException(status_code=422, detail=UNKNOWN_DOC_DETAIL)

    # Overwrite with the decrypted version so the background task reads plain bytes.
    Path(row.storage_path).write_bytes(decrypted)

    row.doc_type = detected
    row.status = "queued"
    row.error = None
    await db.commit()

    background_tasks.add_task(_parse_in_background, doc_id)
    return UploadResponse(id=doc_id, status="queued", deduplicated=False)


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    request: Request,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentOut]:
    result = await db.execute(
        select(Document).where(Document.user_id == user.id).order_by(Document.created_at.desc())
    )
    rows = result.scalars().all()
    dek = get_user_dek(request, user)
    return [document_out_from(r, dek) for r in rows]


@router.get("/{doc_id}", response_model=DocumentOut)
async def get_document(
    doc_id: UUID,
    request: Request,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentOut:
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.user_id == user.id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document_out_from(row, get_user_dek(request, user))


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.user_id == user.id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Best-effort delete the underlying file. DB row removal is the source of truth.
    storage = Path(row.storage_path)
    try:
        storage.unlink(missing_ok=True)
    except OSError as e:
        logger.warning("Failed to remove %s: %s", storage, e)

    await db.delete(row)
    await db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Background task — runs after the response is sent to the browser
# ─────────────────────────────────────────────────────────────────────────────

async def _parse_in_background(doc_id: UUID) -> None:
    """Pulls the row, parses, writes results back. Owns its own DB session.

    Background tasks have no Request scope, so we explicitly load the owning
    user to get their wrapped DEK and unwrap it just for this parse.
    """

    async with SessionLocal() as session:
        row = await session.get(Document, doc_id)
        if row is None:
            logger.error("parse_in_background: document %s missing", doc_id)
            return
        owner = await session.get(User, row.user_id)
        if owner is None or owner.dek_wrapped is None:
            logger.error("parse_in_background: doc %s owner has no DEK; aborting", doc_id)
            row.status = "failed"
            row.error = "Account is missing its encryption key. Please log in and retry."
            await session.commit()
            return
        dek = unwrap_dek(owner.dek_wrapped)
        row.status = "parsing"
        await session.commit()

        try:
            content = Path(row.storage_path).read_bytes()
            if row.doc_type == "form16":
                await _parse_form16(session, row, content, dek)
            elif row.doc_type == "capital_gains":
                await _parse_capital_gains(session, row, content, dek)
            elif row.doc_type == "ais":
                await _parse_ais(session, row, content, dek)
            else:
                raise ParserError(f"No parser registered for doc_type={row.doc_type!r}")
        except (ParserConfigError, CapitalGainsParserError, AisParserConfigError) as e:
            logger.warning("Parser not configured / unavailable: %s", e)
            row.status = "failed"
            row.error = str(e)
            await session.commit()
        except (ParserError, AisParserError) as e:
            logger.exception("Parse failed for %s", doc_id)
            row.status = "failed"
            row.error = str(e)
            await session.commit()
        except Exception as e:  # noqa: BLE001 — last-resort safety net
            logger.exception("Unexpected parse failure for %s", doc_id)
            row.status = "failed"
            row.error = f"Unexpected error: {e}"
            await session.commit()


async def _parse_form16(
    session: AsyncSession, row: Document, pdf_bytes: bytes, dek: bytes
) -> None:
    data, audit = await parse_form16(pdf_bytes)
    parsed = data.model_dump(mode="json")

    # Plaintext metadata used for filtering / lookup — not PII.
    row.ay = data.ay
    row.fy = data.fy
    row.regime = data.regime

    # Encrypted PII / financials.
    row.parsed_json_ct = encrypt_json(dek, parsed)
    row.employer_name_ct = encrypt_str(dek, data.employer.name)
    row.employer_tan_ct = encrypt_str(dek, data.employer.tan)
    row.employee_pan_ct = encrypt_str(dek, data.employee.pan)
    row.gross_salary_ct = encrypt_decimal(dek, data.salary.gross)
    row.total_tds_ct = encrypt_decimal(dek, data.tds.total_tds)
    row.taxable_income_ct = encrypt_decimal(dek, data.taxable_income)
    row.tax_payable_ct = encrypt_decimal(dek, data.tax_payable)

    row.parser_provider = audit.get("provider")
    row.parser_model = audit.get("model")
    row.status = "parsed"
    row.parsed_at = datetime.now(tz=timezone.utc)
    row.error = None
    await session.commit()
    logger.info(
        "parsed form16 %s in=%s out=%s tokens",
        row.id,
        audit.get("input_tokens"),
        audit.get("output_tokens"),
    )


async def _parse_capital_gains(
    session: AsyncSession, row: Document, content: bytes, dek: bytes
) -> None:
    if is_xlsx(content):
        text = xlsx_to_text(content)
        data, audit = await parse_capital_gains_xlsx(text)
    else:
        data, audit = await parse_capital_gains_pdf(content)
    denorm = denorm_capital_gains(data)

    # Plaintext metadata.
    row.broker = denorm.get("broker")
    row.ay = denorm.get("ay")
    row.fy = denorm.get("fy")

    # Encrypted financials + investor PAN.
    row.parsed_json_ct = encrypt_json(dek, data)
    row.stcg_111a_ct = encrypt_decimal(dek, denorm.get("stcg_111a"))
    row.stcg_non_equity_ct = encrypt_decimal(dek, denorm.get("stcg_non_equity"))
    row.ltcg_112a_ct = encrypt_decimal(dek, denorm.get("ltcg_112a"))
    row.ltcg_non_equity_ct = encrypt_decimal(dek, denorm.get("ltcg_non_equity"))
    row.dividends_total_ct = encrypt_decimal(dek, denorm.get("dividends_total"))
    row.exempt_income_total_ct = encrypt_decimal(dek, denorm.get("exempt_income_total"))
    row.total_invested_ct = encrypt_decimal(dek, denorm.get("total_invested"))
    investor = data.get("investor") or {}
    if investor.get("pan"):
        row.employee_pan_ct = encrypt_str(dek, investor["pan"])

    row.parser_provider = audit.get("provider")
    row.parser_model = audit.get("model")
    row.status = "parsed"
    row.parsed_at = datetime.now(tz=timezone.utc)
    row.error = None
    await session.commit()
    logger.info(
        "parsed capital_gains %s broker=%s in=%s out=%s tokens",
        row.id,
        denorm.get("broker"),
        audit.get("input_tokens"),
        audit.get("output_tokens"),
    )


async def _parse_ais(
    session: AsyncSession, row: Document, pdf_bytes: bytes, dek: bytes
) -> None:
    """Parse an AIS / TIS / Form 26AS PDF and persist results.

    AIS aggregates land in the same encrypted columns we already have for
    Form 16 and capital gains (`total_tds_ct`, `dividends_total_ct`,
    `stcg_*_ct`, `ltcg_*_ct`, `exempt_income_total_ct`). The full structured
    breakdown — TDS-by-deductor, interest-by-bank, etc. — lives in
    `parsed_json_ct` for the reconciler to consume.
    """

    data, audit = await parse_ais(pdf_bytes)
    parsed = data.model_dump(mode="json")
    denorm = denorm_ais(data)

    # Plaintext metadata for filtering / lookup.
    row.ay = denorm.get("ay")
    row.fy = denorm.get("fy")

    # Encrypted PII / financials. AIS-reported salary becomes our
    # `gross_salary_ct` cross-check value; AIS total income (TIS only)
    # populates `taxable_income_ct` so the reconciler has a direct compare
    # against Form 16's reported taxable income.
    row.parsed_json_ct = encrypt_json(dek, parsed)
    if data.taxpayer.pan:
        row.employee_pan_ct = encrypt_str(dek, data.taxpayer.pan)
    row.gross_salary_ct = encrypt_decimal(dek, denorm.get("salary_total"))
    row.total_tds_ct = encrypt_decimal(dek, denorm.get("total_tds"))
    row.taxable_income_ct = encrypt_decimal(dek, denorm.get("total_income"))
    row.stcg_111a_ct = encrypt_decimal(dek, denorm.get("stcg_111a"))
    row.stcg_non_equity_ct = encrypt_decimal(dek, denorm.get("stcg_non_equity"))
    row.ltcg_112a_ct = encrypt_decimal(dek, denorm.get("ltcg_112a"))
    row.ltcg_non_equity_ct = encrypt_decimal(dek, denorm.get("ltcg_non_equity"))
    row.dividends_total_ct = encrypt_decimal(dek, denorm.get("dividends_total"))
    row.exempt_income_total_ct = encrypt_decimal(dek, denorm.get("exempt_income_total"))

    row.parser_provider = audit.get("provider")
    row.parser_model = audit.get("model")
    row.status = "parsed"
    row.parsed_at = datetime.now(tz=timezone.utc)
    row.error = None
    await session.commit()
    logger.info(
        "parsed ais %s source=%s in=%s out=%s tokens",
        row.id,
        data.source,
        audit.get("input_tokens"),
        audit.get("output_tokens"),
    )
