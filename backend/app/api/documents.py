"""Documents API: upload Form 16 PDFs, list parsed results.

Upload flow:
  1. Compute sha256, dedup against (user_id, sha256). Re-uploading the same file
     returns the cached row — no Anthropic call.
  2. Otherwise, save bytes to UPLOADS_DIR/<user>/<doc_id>.pdf, insert row with
     status='queued', schedule a FastAPI BackgroundTask.
  3. Background task: status='parsing' → call parse_form16 → status='parsed'
     (and denormalize fields onto the row) or 'failed' with an error message.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import current_user
from app.db.session import SessionLocal, get_db
from app.models import Document, User
from app.schemas.document import DocumentOut, UploadResponse
from app.services.parser.form16 import ParserConfigError, ParserError, parse_form16
from app.services.parser.pdf import decrypt_pdf, is_encrypted

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_DOC_TYPES = {"form16"}
MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15 MB


def _uploads_root() -> Path:
    return Path(get_settings().uploads_dir).resolve()


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    doc_type: str = "form16",
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> UploadResponse:
    if doc_type not in ALLOWED_DOC_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported doc_type: {doc_type}")
    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=415, detail=f"Expected a PDF, got {file.content_type}")

    body = await file.read()
    if len(body) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(body) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File too large (>{MAX_UPLOAD_BYTES // 1024 // 1024} MB)")

    sha256 = hashlib.sha256(body).hexdigest()

    # Dedup: same user + same sha256 → return existing row, no parse re-run
    existing = await db.execute(
        select(Document).where(Document.user_id == user.id, Document.sha256 == sha256)
    )
    existing_row = existing.scalar_one_or_none()
    if existing_row is not None:
        return UploadResponse(id=existing_row.id, status=existing_row.status, deduplicated=True)

    doc_id = uuid4()
    user_dir = _uploads_root() / str(user.id)
    user_dir.mkdir(parents=True, exist_ok=True)
    target = user_dir / f"{doc_id}.pdf"
    target.write_bytes(body)

    # Detect encrypted PDFs up front so we can ask the user for a password
    # before burning Anthropic tokens on a doomed parse.
    try:
        encrypted = is_encrypted(body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    initial_status = "needs_password" if encrypted else "queued"

    row = Document(
        id=doc_id,
        user_id=user.id,
        doc_type=doc_type,
        status=initial_status,
        file_name=file.filename or "form16.pdf",
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
        raise HTTPException(status_code=400, detail=f"Document is not awaiting a password (status={row.status})")

    encrypted_bytes = Path(row.storage_path).read_bytes()
    try:
        decrypted = decrypt_pdf(encrypted_bytes, body.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Overwrite with the decrypted version so the background task reads plain bytes.
    Path(row.storage_path).write_bytes(decrypted)

    row.status = "queued"
    row.error = None
    await db.commit()

    background_tasks.add_task(_parse_in_background, doc_id)
    return UploadResponse(id=doc_id, status="queued", deduplicated=False)


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentOut]:
    result = await db.execute(
        select(Document).where(Document.user_id == user.id).order_by(Document.created_at.desc())
    )
    rows = result.scalars().all()
    return [DocumentOut.model_validate(r) for r in rows]


@router.get("/{doc_id}", response_model=DocumentOut)
async def get_document(
    doc_id: UUID,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentOut:
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.user_id == user.id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return DocumentOut.model_validate(row)


# ─────────────────────────────────────────────────────────────────────────────
# Background task — runs after the response is sent to the browser
# ─────────────────────────────────────────────────────────────────────────────

async def _parse_in_background(doc_id: UUID) -> None:
    """Pulls the row, parses, writes results back. Owns its own DB session."""

    async with SessionLocal() as session:
        row = await session.get(Document, doc_id)
        if row is None:
            logger.error("parse_in_background: document %s missing", doc_id)
            return
        row.status = "parsing"
        await session.commit()

        try:
            pdf_bytes = Path(row.storage_path).read_bytes()
            data, audit = await parse_form16(pdf_bytes)
        except ParserConfigError as e:
            logger.warning("Parser not configured: %s", e)
            row.status = "failed"
            row.error = str(e)
            await session.commit()
            return
        except ParserError as e:
            logger.exception("Form16 parse failed for %s", doc_id)
            row.status = "failed"
            row.error = str(e)
            await session.commit()
            return
        except Exception as e:  # noqa: BLE001 — last-resort safety net
            logger.exception("Unexpected parse failure for %s", doc_id)
            row.status = "failed"
            row.error = f"Unexpected error: {e}"
            await session.commit()
            return

        # Denormalize for fast queries / UI display
        row.parsed_json = data.model_dump(mode="json")
        row.ay = data.ay
        row.fy = data.fy
        row.employer_name = data.employer.name
        row.employer_tan = data.employer.tan
        row.employee_pan = data.employee.pan
        row.gross_salary = data.salary.gross
        row.total_tds = data.tds.total_tds
        row.taxable_income = data.taxable_income
        row.tax_payable = data.tax_payable
        row.regime = data.regime
        row.parser_provider = audit.get("provider")
        row.parser_model = audit.get("model")
        row.status = "parsed"
        row.parsed_at = datetime.now(tz=timezone.utc)
        row.error = None
        await session.commit()
        logger.info(
            "parsed doc %s in=%s out=%s tokens",
            doc_id,
            audit.get("input_tokens"),
            audit.get("output_tokens"),
        )
