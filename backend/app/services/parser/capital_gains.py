"""Capital gains parser — Anthropic Claude Haiku, aggregate-level extraction.

Schema captures the four main buckets the IT Act treats differently:
  - STCG @ 111A (equity, taxed at 20% post-Jul 2024)
  - STCG non-equity (debt etc., taxed at slab rates)
  - LTCG @ 112A (equity, first ₹1.25L exempt; rest at 12.5%)
  - LTCG non-equity (debt, taxed at slab post-Apr 2023)
plus dividends and other exempt income (10(15), 10(11A), etc.).

Intentionally aggregate-only — trade-level extraction comes when we wire the
ITR-2 Schedule CG generator.
"""

from __future__ import annotations

import base64
import logging

from anthropic import APIError, AsyncAnthropic, BadRequestError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


EXTRACTION_PROMPT = """\
You are a tax document parser. The PDF above is an Indian capital-gains
statement. It could come from a stockbroker (Zerodha, Groww, Upstox, Angel One,
5paisa, ICICI Direct, HDFC Securities, etc.) or a CAMS / KFinTech consolidated
mutual fund account statement (CAS).

Extract the four capital-gains buckets and call `extract_capital_gains` exactly
once with the structured data. Rules:

- Identify the broker / source from the document branding and put it in `broker`
  (lowercase, e.g. "zerodha", "groww", "cams", "kfintech"). If unclear, omit it.
- Aggregate totals only — do NOT enumerate every trade. Just the bucket totals
  and the trade count where reported.
- Bucket definitions:
    * stcg_111a       = STCG on listed equity / equity MFs (Section 111A) — 20% rate
    * stcg_non_equity = STCG on debt / non-equity (slab rates)
    * ltcg_112a       = LTCG on listed equity / equity MFs (Section 112A) — 12.5% above ₹1.25L
    * ltcg_non_equity = LTCG on debt / non-equity (slab post Apr 2023)
- Use Indian rupee values as numeric amounts (e.g. 23000.50, no commas/symbols).
- `ay` is the Assessment Year (e.g. "2026-27"); `fy` is the Financial Year
  (e.g. "2025-26"). Read directly from the document.
- For dividends, list a few line items if reported, plus a total.
- For exempt income (PPF / EPF interest, tax-free bonds, agricultural income),
  list the section code where shown (e.g. "10(15)", "10(11A)") and amount.
- For `total_invested`: sum the **buy values** across every transaction and every
  open position in the document — equity, F&O, mutual funds, bonds — i.e. total
  capital deployed. If the document doesn't show buy values directly, leave it
  unset rather than guess.
- If a field is not visible or not applicable, omit it (do not invent values).
"""


CAPITAL_GAINS_TOOL = {
    "name": "extract_capital_gains",
    "description": "Submit the structured aggregate capital-gains data extracted from the PDF.",
    "input_schema": {
        "type": "object",
        "properties": {
            "broker": {
                "type": "string",
                "description": "Lowercase identifier: 'zerodha', 'groww', 'upstox', 'angel_one', "
                               "'icici_direct', 'cams', 'kfintech', etc.",
            },
            "ay": {"type": "string", "description": "Assessment year, e.g. '2026-27'"},
            "fy": {"type": "string", "description": "Financial year, e.g. '2025-26'"},
            "investor": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "pan": {"type": "string"},
                },
            },
            "stcg": {
                "type": "object",
                "properties": {
                    "equity_111a": {
                        "type": "object",
                        "properties": {
                            "total_gain": {"type": "number"},
                            "trades_count": {"type": "integer"},
                        },
                    },
                    "non_equity": {
                        "type": "object",
                        "properties": {
                            "total_gain": {"type": "number"},
                            "trades_count": {"type": "integer"},
                        },
                    },
                },
            },
            "ltcg": {
                "type": "object",
                "properties": {
                    "equity_112a": {
                        "type": "object",
                        "properties": {
                            "total_gain": {"type": "number"},
                            "trades_count": {"type": "integer"},
                            "exempt_threshold": {
                                "type": "number",
                                "description": "₹1,25,000 for AY 2025-26+; ₹1,00,000 earlier",
                            },
                        },
                    },
                    "non_equity": {
                        "type": "object",
                        "properties": {
                            "total_gain": {"type": "number"},
                            "trades_count": {"type": "integer"},
                        },
                    },
                },
            },
            "dividends": {
                "type": "object",
                "properties": {
                    "total": {"type": "number"},
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "company": {"type": "string"},
                                "amount": {"type": "number"},
                            },
                            "required": ["amount"],
                        },
                    },
                },
            },
            "exempt_income": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "section": {"type": "string", "description": "e.g. '10(15)', '10(11A)'"},
                        "label": {"type": "string"},
                        "amount": {"type": "number"},
                    },
                    "required": ["label", "amount"],
                },
            },
            "total_invested": {
                "type": "number",
                "description": "Sum of buy values across every trade and open position in the document.",
            },
        },
    },
}


class CapitalGainsParserError(RuntimeError):
    pass


async def parse_capital_gains_pdf(pdf_bytes: bytes) -> tuple[dict, dict]:
    """Parse a capital-gains PDF (CAMS/KFinTech CAS, broker PDFs)."""

    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("ascii")
    content = [
        {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": pdf_b64,
            },
        },
        {"type": "text", "text": EXTRACTION_PROMPT},
    ]
    return await _call_claude(content)


async def parse_capital_gains_xlsx(xlsx_text: str) -> tuple[dict, dict]:
    """Parse a capital-gains XLSX rendered to text (Zerodha, Groww, Upstox, etc.)."""

    content = [
        {"type": "text", "text": f"{EXTRACTION_PROMPT}\n\n--- Spreadsheet content ---\n\n{xlsx_text}"},
    ]
    return await _call_claude(content)


async def _call_claude(content: list[dict]) -> tuple[dict, dict]:
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise CapitalGainsParserError(
            "ANTHROPIC_API_KEY is not set. Add it to backend/.env and restart the server."
        )

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    try:
        response = await client.messages.create(
            model=settings.parser_model,
            max_tokens=2048,
            messages=[{"role": "user", "content": content}],
            tools=[CAPITAL_GAINS_TOOL],
            tool_choice={"type": "tool", "name": "extract_capital_gains"},
        )
    except BadRequestError as e:
        raise CapitalGainsParserError(f"Anthropic rejected the request: {e}") from e
    except APIError as e:
        raise CapitalGainsParserError(f"Anthropic API error: {e}") from e

    tool_block = next((b for b in response.content if b.type == "tool_use"), None)
    if tool_block is None:
        raise CapitalGainsParserError("Model did not return a tool_use block.")

    data: dict = dict(tool_block.input)  # type: ignore[arg-type]
    data.setdefault("schema_version", 1)

    audit = {
        "provider": "anthropic",
        "model": settings.parser_model,
        "stop_reason": response.stop_reason,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }
    return data, audit


# ─────────────────────────────────────────────────────────────────────────────
# Helpers used by the API layer to denormalize CG data onto the documents row
# ─────────────────────────────────────────────────────────────────────────────

def denorm_capital_gains(parsed: dict) -> dict:
    """Pull out the scalar fields we cache on the documents row for fast queries."""

    def _get(d: dict | None, path: list[str], default=None):
        cur = d
        for k in path:
            if not isinstance(cur, dict):
                return default
            cur = cur.get(k)
        return cur if cur is not None else default

    out: dict = {
        "broker": parsed.get("broker"),
        "ay": parsed.get("ay"),
        "fy": parsed.get("fy"),
        "stcg_111a": _get(parsed, ["stcg", "equity_111a", "total_gain"]),
        "stcg_non_equity": _get(parsed, ["stcg", "non_equity", "total_gain"]),
        "ltcg_112a": _get(parsed, ["ltcg", "equity_112a", "total_gain"]),
        "ltcg_non_equity": _get(parsed, ["ltcg", "non_equity", "total_gain"]),
        "dividends_total": _get(parsed, ["dividends", "total"]),
        "total_invested": parsed.get("total_invested"),
    }

    exempt_items = parsed.get("exempt_income") or []
    if isinstance(exempt_items, list):
        total_exempt = 0.0
        for it in exempt_items:
            try:
                total_exempt += float(it.get("amount") or 0)
            except (TypeError, ValueError):
                pass
        out["exempt_income_total"] = total_exempt if total_exempt > 0 else None

    return out
