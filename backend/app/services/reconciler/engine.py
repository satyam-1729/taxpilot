"""Reconciliation engine — pure function over already-decrypted parsed_json blobs.

Coverage in this first pass:
  1. TDS by deductor (TAN-keyed) — Form 16 vs AIS Part B
  2. Salary total                — Σ Form 16 gross vs AIS section-192 total
  3. Capital gains aggregates    — broker P&L vs AIS capital_gains
  4. Dividends total             — broker P&L vs AIS dividends_total

Each comparison returns zero or more Mismatch records. The API layer scopes
inputs to a single FY before calling reconcile().
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

Severity = Literal["error", "warning", "info"]

# Tolerance for "this is rounding noise, ignore it". AIS rounds to whole rupees;
# Form 16 sometimes has paise. ₹50 absolute, 1% relative — both required.
TOLERANCE_ABS = Decimal("50")
TOLERANCE_REL = Decimal("0.01")


@dataclass(frozen=True)
class Mismatch:
    """A single reconciliation finding the user must review.

    `source_a` and `source_b` are (label, amount) tuples; `delta = b - a` so a
    positive delta means AIS (B) is higher than our docs (A) — the under-
    reporting direction.
    """

    severity: Severity
    code: str  # stable id, e.g. "tds_deductor_missing", "salary_total_delta"
    fact: str
    source_a: tuple[str, Decimal | None]
    source_b: tuple[str, Decimal | None]
    delta: Decimal | None
    suggestion: str

    def to_dict(self) -> dict:
        def pair(p: tuple[str, Decimal | None]) -> dict:
            return {"label": p[0], "amount": _decimal_to_jsonable(p[1])}

        return {
            "severity": self.severity,
            "code": self.code,
            "fact": self.fact,
            "source_a": pair(self.source_a),
            "source_b": pair(self.source_b),
            "delta": _decimal_to_jsonable(self.delta),
            "suggestion": self.suggestion,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────


def reconcile(
    *,
    form16_docs: list[dict],
    capital_gains_docs: list[dict],
    ais_docs: list[dict],
) -> list[Mismatch]:
    """Compare parsed docs and return findings, in stable severity order.

    Each list element is the decrypted `parsed_json` payload for one document
    (already filtered to a single FY by the caller). Pass empty lists for
    sources the user hasn't uploaded — the reconciler degrades gracefully.
    """

    findings: list[Mismatch] = []

    if not ais_docs:
        # Without AIS we have nothing to reconcile against. Surface that as
        # info so the UI can prompt for AIS upload.
        if form16_docs or capital_gains_docs:
            findings.append(
                Mismatch(
                    severity="info",
                    code="ais_missing",
                    fact="AIS not uploaded",
                    source_a=("uploaded docs", None),
                    source_b=("ais", None),
                    delta=None,
                    suggestion=(
                        "Upload your AIS / Form 26AS so we can cross-check TDS, "
                        "interest, dividends and capital gains against what the "
                        "Income Tax Department has on file."
                    ),
                )
            )
        return findings

    # Multiple AIS documents for the same FY: prefer the most recent, but for
    # entry-level diffs we union TDS rows across all AIS payloads — the IT
    # Dept publishes incrementally, and a row missing from one AIS may be in
    # another. Aggregates use the maximum across AIS docs (most-recent proxy).
    findings.extend(_reconcile_tds(form16_docs, ais_docs))
    findings.extend(_reconcile_salary(form16_docs, ais_docs))
    findings.extend(_reconcile_capital_gains(capital_gains_docs, ais_docs))
    findings.extend(_reconcile_dividends(capital_gains_docs, ais_docs))

    # Stable severity ordering: errors first, then warnings, then info.
    severity_rank = {"error": 0, "warning": 1, "info": 2}
    findings.sort(key=lambda m: (severity_rank[m.severity], m.code))
    return findings


# ─────────────────────────────────────────────────────────────────────────────
# TDS by deductor
# ─────────────────────────────────────────────────────────────────────────────


def _reconcile_tds(form16_docs: list[dict], ais_docs: list[dict]) -> list[Mismatch]:
    """Match TDS rows by TAN. Identifies missing deductors and per-employer deltas."""

    # Form 16 keyed by TAN. If TAN is missing (rare but happens with old
    # Form 16s) fall back to a normalized employer name.
    f16_by_tan: dict[str, dict] = {}
    for doc in form16_docs:
        employer = (doc.get("employer") or {})
        tan = _norm_tan(employer.get("tan"))
        name = _norm_name(employer.get("name"))
        key = tan or f"name:{name}" if name else None
        if not key:
            continue
        existing = f16_by_tan.get(key, {"name": employer.get("name"), "tan": tan, "tds": Decimal(0)})
        total_tds = _D(_get(doc, "tds.total_tds"))
        if total_tds is not None:
            existing["tds"] = (existing.get("tds") or Decimal(0)) + total_tds
        f16_by_tan[key] = existing

    # AIS Part B aggregated to (TAN, section=192). Salary deductors only —
    # 194A/194/etc. are not in Form 16's scope, so we don't pair them.
    ais_by_tan: dict[str, dict] = {}
    for doc in ais_docs:
        for entry in doc.get("tds_entries") or []:
            section = (entry.get("section") or "").strip()
            if section != "192":
                continue
            tan = _norm_tan(entry.get("deductor_tan"))
            name = _norm_name(entry.get("deductor_name"))
            key = tan or f"name:{name}" if name else None
            if not key:
                continue
            agg = ais_by_tan.get(key, {"name": entry.get("deductor_name"), "tan": tan, "tds": Decimal(0)})
            tds = _D(entry.get("tds_deducted"))
            if tds is not None:
                agg["tds"] = (agg.get("tds") or Decimal(0)) + tds
            ais_by_tan[key] = agg

    out: list[Mismatch] = []

    # A. AIS deductors not in Form 16 — biggest red flag (missing employer).
    for key, ais_row in ais_by_tan.items():
        if key in f16_by_tan:
            continue
        deductor = ais_row.get("name") or "Unknown employer"
        out.append(
            Mismatch(
                severity="error",
                code="tds_deductor_missing_form16",
                fact=f"Salary from {deductor}",
                source_a=("form16", None),
                source_b=("ais", ais_row.get("tds")),
                delta=ais_row.get("tds"),
                suggestion=(
                    f"AIS shows TDS u/s 192 from {deductor}"
                    + (f" (TAN {ais_row['tan']})" if ais_row.get("tan") else "")
                    + ". Upload that employer's Form 16 or confirm the salary was correctly reported."
                ),
            )
        )

    # B. Form 16 deductors not in AIS — usually means the employer hasn't
    # deposited TDS yet. Surface as a warning, not an error: AIS is updated
    # progressively and this often resolves itself by the filing deadline.
    for key, f16_row in f16_by_tan.items():
        if key in ais_by_tan:
            continue
        deductor = f16_row.get("name") or "Unknown employer"
        out.append(
            Mismatch(
                severity="warning",
                code="tds_deductor_missing_ais",
                fact=f"Form 16 from {deductor}",
                source_a=("form16", f16_row.get("tds")),
                source_b=("ais", None),
                delta=None,
                suggestion=(
                    f"Form 16 from {deductor} hasn't appeared in AIS yet. AIS is "
                    "published progressively; if this persists past July, ask the "
                    "employer to confirm they've filed the TDS return."
                ),
            )
        )

    # C. Both sides report this deductor — diff the TDS amount.
    for key in f16_by_tan.keys() & ais_by_tan.keys():
        f16_amt = f16_by_tan[key].get("tds") or Decimal(0)
        ais_amt = ais_by_tan[key].get("tds") or Decimal(0)
        delta = ais_amt - f16_amt
        if _within_tolerance(f16_amt, ais_amt):
            continue
        deductor = ais_by_tan[key].get("name") or f16_by_tan[key].get("name") or "Unknown"
        if delta > 0:
            severity: Severity = "error"
            suggestion = (
                f"AIS shows ₹{delta} more TDS from {deductor} than your Form 16. "
                "Ask the employer for a corrected Form 16, or claim the AIS amount "
                "and keep a screenshot."
            )
        else:
            severity = "warning"
            suggestion = (
                f"Form 16 shows ₹{-delta} more TDS than AIS from {deductor}. "
                "AIS may not be fully updated yet; recheck close to the filing deadline."
            )
        out.append(
            Mismatch(
                severity=severity,
                code="tds_deductor_amount_mismatch",
                fact=f"TDS u/s 192 — {deductor}",
                source_a=("form16", f16_amt),
                source_b=("ais", ais_amt),
                delta=delta,
                suggestion=suggestion,
            )
        )

    return out


# ─────────────────────────────────────────────────────────────────────────────
# Salary total
# ─────────────────────────────────────────────────────────────────────────────


def _reconcile_salary(form16_docs: list[dict], ais_docs: list[dict]) -> list[Mismatch]:
    """Σ Form 16 gross vs AIS section-192 'amount paid' across all employers."""

    f16_total = Decimal(0)
    f16_seen = False
    for doc in form16_docs:
        gross = _D(_get(doc, "salary.gross"))
        if gross is None:
            continue
        f16_total += gross
        f16_seen = True

    if not f16_seen:
        return []  # nothing to compare; caller already handles "no form 16" upstream

    ais_total = Decimal(0)
    for doc in ais_docs:
        if (s := _D(doc.get("salary_total"))) is not None:
            ais_total = max(ais_total, s)
            continue
        # Fallback: sum amount_paid from section-192 entries.
        derived = Decimal(0)
        for entry in doc.get("tds_entries") or []:
            if (entry.get("section") or "").strip() != "192":
                continue
            amt = _D(entry.get("amount_paid"))
            if amt is not None:
                derived += amt
        ais_total = max(ais_total, derived)

    if ais_total == 0 or _within_tolerance(f16_total, ais_total):
        return []

    delta = ais_total - f16_total
    if delta > 0:
        return [
            Mismatch(
                severity="error",
                code="salary_total_under_reported",
                fact="Total salary",
                source_a=("form16", f16_total),
                source_b=("ais", ais_total),
                delta=delta,
                suggestion=(
                    f"AIS reports ₹{delta} more salary than the Form 16(s) you uploaded. "
                    "Either an employer's Form 16 is missing or a Form 16 understates "
                    "gross salary. Resolve before filing."
                ),
            )
        ]
    # Form 16 > AIS: AIS still catching up.
    return [
        Mismatch(
            severity="warning",
            code="salary_total_ais_lagging",
            fact="Total salary",
            source_a=("form16", f16_total),
            source_b=("ais", ais_total),
            delta=delta,
            suggestion=(
                "Form 16 shows more salary than AIS — usually means an employer "
                "hasn't filed the final TDS return yet. Recheck closer to filing."
            ),
        )
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Capital gains aggregates
# ─────────────────────────────────────────────────────────────────────────────


_CG_BUCKETS = [
    ("stcg_111a",       "STCG on listed equity (111A)"),
    ("stcg_non_equity", "STCG on debt / non-equity"),
    ("ltcg_112a",       "LTCG on listed equity (112A)"),
    ("ltcg_non_equity", "LTCG on debt / non-equity"),
]


def _reconcile_capital_gains(
    capital_gains_docs: list[dict], ais_docs: list[dict]
) -> list[Mismatch]:
    """Per-bucket diff. AIS only carries bucket-tagged values when the document
    explicitly labels them (often only in TIS); skip silently when absent."""

    out: list[Mismatch] = []
    # Sum across every broker / CAS we have for the FY.
    cg_totals: dict[str, Decimal] = {b: Decimal(0) for b, _ in _CG_BUCKETS}
    cg_seen = False
    for doc in capital_gains_docs:
        for bucket, _ in _CG_BUCKETS:
            head, key = ("stcg", "equity_111a") if bucket == "stcg_111a" \
                else ("stcg", "non_equity") if bucket == "stcg_non_equity" \
                else ("ltcg", "equity_112a") if bucket == "ltcg_112a" \
                else ("ltcg", "non_equity")
            v = _D(_get(doc, f"{head}.{key}.total_gain"))
            if v is not None:
                cg_totals[bucket] += v
                cg_seen = True

    if not cg_seen:
        return []

    ais_totals: dict[str, Decimal | None] = {b: None for b, _ in _CG_BUCKETS}
    for doc in ais_docs:
        cg = doc.get("capital_gains") or {}
        for bucket, _ in _CG_BUCKETS:
            v = _D(cg.get(bucket))
            if v is None:
                continue
            cur = ais_totals[bucket]
            ais_totals[bucket] = v if cur is None else max(cur, v)

    for bucket, label in _CG_BUCKETS:
        ais_v = ais_totals[bucket]
        if ais_v is None:
            continue  # AIS didn't tag this bucket — common for plain AIS PDFs
        broker_v = cg_totals[bucket]
        if _within_tolerance(broker_v, ais_v):
            continue
        delta = ais_v - broker_v
        severity: Severity = "error" if delta > 0 else "warning"
        suggestion = (
            f"AIS reports ₹{delta} more {label} than your broker P&L. "
            "Check for missing demat accounts, bonus issues, or buybacks."
        ) if delta > 0 else (
            f"Broker reports ₹{-delta} more {label} than AIS. "
            "AIS may be lagging; recheck before filing."
        )
        out.append(
            Mismatch(
                severity=severity,
                code=f"capital_gains_{bucket}",
                fact=label,
                source_a=("broker", broker_v),
                source_b=("ais", ais_v),
                delta=delta,
                suggestion=suggestion,
            )
        )
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Dividends
# ─────────────────────────────────────────────────────────────────────────────


def _reconcile_dividends(
    capital_gains_docs: list[dict], ais_docs: list[dict]
) -> list[Mismatch]:
    """Total dividend income — broker P&L vs AIS SFT-015."""

    broker_total = Decimal(0)
    broker_seen = False
    for doc in capital_gains_docs:
        v = _D(_get(doc, "dividends.total"))
        if v is not None:
            broker_total += v
            broker_seen = True

    ais_total: Decimal | None = None
    for doc in ais_docs:
        v = _D(doc.get("dividends_total"))
        if v is None:
            continue
        ais_total = v if ais_total is None else max(ais_total, v)

    if ais_total is None:
        return []

    if not broker_seen and ais_total > 0:
        return [
            Mismatch(
                severity="error",
                code="dividends_missing_broker",
                fact="Dividend income",
                source_a=("broker", None),
                source_b=("ais", ais_total),
                delta=ais_total,
                suggestion=(
                    f"AIS reports ₹{ais_total} of dividend income that isn't in any "
                    "broker statement you uploaded. Add it to 'income from other "
                    "sources' or upload the corresponding broker / CAS."
                ),
            )
        ]

    if _within_tolerance(broker_total, ais_total):
        return []
    delta = ais_total - broker_total
    severity: Severity = "error" if delta > 0 else "warning"
    suggestion = (
        f"AIS reports ₹{delta} more dividend income than your broker P&L. "
        "Likely a missing demat across brokers."
    ) if delta > 0 else (
        f"Broker reports ₹{-delta} more dividends than AIS. AIS may be lagging."
    )
    return [
        Mismatch(
            severity=severity,
            code="dividends_total_mismatch",
            fact="Dividend income",
            source_a=("broker", broker_total),
            source_b=("ais", ais_total),
            delta=delta,
            suggestion=suggestion,
        )
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _D(v: Any) -> Decimal | None:
    """Coerce JSON numbers / strings into Decimal, returning None for None/empty."""
    if v is None or v == "":
        return None
    try:
        return Decimal(str(v))
    except Exception:
        return None


def _get(d: dict, path: str) -> Any:
    """Dotted-path lookup that returns None on any missing/non-dict segment."""
    cur: Any = d
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _norm_tan(v: Any) -> str | None:
    if not v:
        return None
    s = str(v).strip().upper()
    return s or None


def _norm_name(v: Any) -> str | None:
    if not v:
        return None
    s = str(v).strip().upper()
    return s or None


def _within_tolerance(a: Decimal, b: Decimal) -> bool:
    """True if |a - b| is within both the absolute and relative tolerances.

    Both must hold, so a 0.5% delta on a ₹40L salary is NOT noise (₹20K — way
    over TOLERANCE_ABS), but ₹40 on a ₹40L salary IS.
    """
    diff = abs(a - b)
    if diff > TOLERANCE_ABS:
        return False
    base = max(abs(a), abs(b))
    if base == 0:
        return True
    return diff / base <= TOLERANCE_REL


def _decimal_to_jsonable(v: Decimal | None) -> float | None:
    if v is None:
        return None
    return float(v)
