"""AIS / TIS / Form 26AS parser using Anthropic Claude with PDF input + tool-use.

The Annual Information Statement is the IT Dept's consolidated ledger of every
financial transaction reported against a PAN. We send the PDF as a `document`
content block and force the model to call `extract_ais` — a tool whose JSON
schema mirrors `AisData`.

AIS PDFs are typically large (50+ pages with many SFT entries). We ask the model
to keep TDS rows row-level (the reconciler needs deductor identity to match
against Form 16 and bank statements) but to roll up SFT detail into per-payer
totals — every securities trade is not useful here, only the bucket totals.
"""

from __future__ import annotations

import base64
import logging

from anthropic import APIError, AsyncAnthropic, BadRequestError

from app.core.config import get_settings
from app.schemas.document import AisData

logger = logging.getLogger(__name__)


EXTRACTION_PROMPT = """\
You are a tax document parser. The PDF above is one of:
  - **AIS** (Annual Information Statement, issued by the Indian Income Tax Department)
  - **TIS** (Taxpayer Information Summary, the simplified roll-up of AIS)
  - **Form 26AS** (older tax credit statement — narrower than AIS but overlapping)

Read the document and call the `extract_ais` tool exactly once with the
structured data. Rules:

- Set `source` to "ais", "tis", or "26as" based on the document title/header.
- `ay` is the Assessment Year (e.g. "2026-27"); `fy` is the Financial Year
  (e.g. "2025-26"). Read directly from the header.
- `taxpayer.aadhaar_last4` only if shown (AIS often shows "XXXX XXXX 1234");
  leave blank otherwise. Never invent.

TDS / TCS entries (Part B of AIS, Part A of 26AS):
- Emit ONE entry per (deductor, section). If the same deductor appears across
  multiple quarters, sum and emit a single row with the total.
- `section` is the IT Act section under which TDS was deducted: "192" for
  salary, "194A" for interest, "194" for dividends, "194I" for rent, etc.
- `total_tds` is the grand total across every TDS/TCS entry in the document.
- `salary_total` = sum of `amount_paid` where section == "192" (salary TDS).

Interest income (SFT-016 / Part E):
- ONE entry per bank or payer. If a bank reports multiple accounts, emit
  separate entries when account-last4 is visible; otherwise sum into one row.
- `interest_total` = sum across every entry.

Dividends (SFT-015 / Part E "Dividend"):
- ONE entry per company / ISIN where shown.
- `dividends_total` = sum across every entry.

Capital gains (Part E "Sale of securities and units of mutual fund"):
- The IT Dept does NOT publish bucket-tagged STCG/LTCG numbers in AIS the way
  brokers do — AIS shows gross sale value. Set the four `capital_gains.*`
  fields ONLY if the document explicitly labels them as STCG-111A, LTCG-112A,
  etc. (TIS sometimes does). If only gross sale value is shown, leave them unset.

Other income:
- Anything not covered above: rent received (194I), professional receipts (194J),
  business receipts (194Q), interest on income tax refunds, etc. One row per
  income head with the section code where shown.

Tax payments:
- `advance_tax_paid` = sum of advance-tax challans (Part C of 26AS).
- `self_assessment_tax_paid` = sum of self-assessment-tax challans.
- `refunds_received` = sum of refunds paid by IT Dept (Part D of 26AS).

Exempt income:
- `exempt_income_total` is the total of items explicitly marked exempt in AIS
  (PPF interest, EPF interest, tax-free bonds u/s 10(15), agricultural income,
  etc.). If unclear or not separately tabulated, leave unset rather than guess.

TIS-only fields:
- If this is a TIS document, fill `total_income_reported` with the
  taxpayer-summary total income. For AIS / 26AS, leave it unset.

General:
- Use Indian rupee values as numeric amounts (e.g. 23000.50, no commas/symbols).
- If a field is not visible or not applicable, omit it (do not invent values).
- Negative amounts (refunds, losses) keep their sign.
"""


# Tool schema mirrors AisData. Kept inline so prompt + schema travel together.
AIS_TOOL = {
    "name": "extract_ais",
    "description": "Submit the structured data extracted from the AIS / TIS / Form 26AS PDF.",
    "input_schema": {
        "type": "object",
        "properties": {
            "source": {"type": "string", "enum": ["ais", "tis", "26as"]},
            "ay": {"type": "string", "description": "Assessment year, e.g. '2026-27'"},
            "fy": {"type": "string", "description": "Financial year, e.g. '2025-26'"},
            "taxpayer": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "pan": {"type": "string"},
                    "aadhaar_last4": {"type": "string"},
                },
            },
            "tds_entries": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "deductor_name": {"type": "string"},
                        "deductor_tan": {"type": "string"},
                        "section": {"type": "string"},
                        "amount_paid": {"type": "number"},
                        "tds_deducted": {"type": "number"},
                    },
                },
            },
            "total_tds": {"type": "number"},
            "salary_total": {"type": "number"},
            "interest_income": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "payer_name": {"type": "string"},
                        "account_last4": {"type": "string"},
                        "section": {"type": "string"},
                        "amount": {"type": "number"},
                    },
                    "required": ["amount"],
                },
            },
            "interest_total": {"type": "number"},
            "dividends": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "payer_name": {"type": "string"},
                        "isin": {"type": "string"},
                        "amount": {"type": "number"},
                    },
                    "required": ["amount"],
                },
            },
            "dividends_total": {"type": "number"},
            "capital_gains": {
                "type": "object",
                "properties": {
                    "stcg_111a": {"type": "number"},
                    "stcg_non_equity": {"type": "number"},
                    "ltcg_112a": {"type": "number"},
                    "ltcg_non_equity": {"type": "number"},
                },
            },
            "other_income": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string"},
                        "section": {"type": "string"},
                        "amount": {"type": "number"},
                    },
                    "required": ["label", "amount"],
                },
            },
            "exempt_income_total": {"type": "number"},
            "advance_tax_paid": {"type": "number"},
            "self_assessment_tax_paid": {"type": "number"},
            "refunds_received": {"type": "number"},
            "total_income_reported": {"type": "number"},
        },
    },
}


class AisParserError(RuntimeError):
    pass


class AisParserConfigError(RuntimeError):
    pass


async def parse_ais(pdf_bytes: bytes) -> tuple[AisData, dict]:
    """Parse an AIS / TIS / Form 26AS PDF and return (typed data, audit metadata)."""

    settings = get_settings()
    if not settings.anthropic_api_key:
        raise AisParserConfigError(
            "ANTHROPIC_API_KEY is not set. Add it to backend/.env and restart the server."
        )

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("ascii")

    try:
        response = await client.messages.create(
            model=settings.parser_model,
            max_tokens=8192,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_b64,
                            },
                        },
                        {"type": "text", "text": EXTRACTION_PROMPT},
                    ],
                }
            ],
            tools=[AIS_TOOL],
            tool_choice={"type": "tool", "name": "extract_ais"},
        )
    except BadRequestError as e:
        raise AisParserError(f"Anthropic rejected the request: {e}") from e
    except APIError as e:
        raise AisParserError(f"Anthropic API error: {e}") from e

    tool_block = next((b for b in response.content if b.type == "tool_use"), None)
    if tool_block is None:
        raise AisParserError("Model did not return a tool_use block.")

    raw_input: dict = tool_block.input  # type: ignore[assignment]
    try:
        data = AisData.model_validate(raw_input)
    except Exception as e:
        logger.exception("AIS schema validation failed", extra={"raw": raw_input})
        raise AisParserError(f"Schema validation failed: {e}") from e

    audit = {
        "provider": "anthropic",
        "model": settings.parser_model,
        "stop_reason": response.stop_reason,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }
    return data, audit


# ─────────────────────────────────────────────────────────────────────────────
# Helper used by the API layer to denormalize AIS data onto the documents row
# ─────────────────────────────────────────────────────────────────────────────

def denorm_ais(data: AisData) -> dict:
    """Pull the headline aggregates we cache on the documents row.

    Capital-gains figures are only carried over when AIS actually labels them
    as STCG-111A / LTCG-112A — gross sale value alone is not enough.
    """

    return {
        "ay": data.ay,
        "fy": data.fy,
        "total_tds": data.total_tds,
        "salary_total": data.salary_total,
        "dividends_total": data.dividends_total,
        "exempt_income_total": data.exempt_income_total,
        "stcg_111a": data.capital_gains.stcg_111a,
        "stcg_non_equity": data.capital_gains.stcg_non_equity,
        "ltcg_112a": data.capital_gains.ltcg_112a,
        "ltcg_non_equity": data.capital_gains.ltcg_non_equity,
        "total_income": data.total_income_reported,
    }
