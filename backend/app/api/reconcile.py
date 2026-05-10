"""Reconciliation API — surfaces cross-source mismatches for a given FY.

Recomputes from the user's current documents on every call. Cheap (in-memory
diff over decrypted parsed_json blobs); no caching at this layer. If we ever
need to persist, add a `reconciliations` table — for now, idempotent on read.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import current_user, get_user_dek
from app.db.session import get_db
from app.models import Document, User
from app.services.reconciler import reconcile
from app.utils.crypto import read_json

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reconcile", tags=["reconcile"])


@router.get("")
async def reconcile_for_fy(
    request: Request,
    fy: str = Query(..., description="Financial year, e.g. '2025-26'"),
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return reconciliation findings for a single FY.

    Output shape:
      {
        "fy": "2025-26",
        "doc_counts": {"form16": 2, "capital_gains": 1, "ais": 1},
        "findings": [{ severity, code, fact, source_a, source_b, delta, suggestion }, ...],
        "summary": {"errors": 1, "warnings": 2, "info": 0}
      }
    """

    dek = get_user_dek(request, user)

    # We compare on FY, but store FY *and* AY on each row. ay/fy are populated
    # post-parse from the parser output, so rows still in 'queued' / 'parsing'
    # status are skipped.
    result = await db.execute(
        select(Document).where(
            Document.user_id == user.id,
            Document.status == "parsed",
            Document.fy == fy,
        )
    )
    rows = result.scalars().all()

    form16_payloads: list[dict] = []
    cg_payloads: list[dict] = []
    ais_payloads: list[dict] = []

    for row in rows:
        parsed = read_json(row.parsed_json_ct, dek)
        if not isinstance(parsed, dict):
            continue
        if row.doc_type == "form16":
            form16_payloads.append(parsed)
        elif row.doc_type == "capital_gains":
            cg_payloads.append(parsed)
        elif row.doc_type == "ais":
            ais_payloads.append(parsed)

    findings = reconcile(
        form16_docs=form16_payloads,
        capital_gains_docs=cg_payloads,
        ais_docs=ais_payloads,
    )

    summary = {"errors": 0, "warnings": 0, "info": 0}
    for f in findings:
        bucket = {"error": "errors", "warning": "warnings", "info": "info"}[f.severity]
        summary[bucket] += 1

    return {
        "fy": fy,
        "doc_counts": {
            "form16": len(form16_payloads),
            "capital_gains": len(cg_payloads),
            "ais": len(ais_payloads),
        },
        "findings": [f.to_dict() for f in findings],
        "summary": summary,
    }
