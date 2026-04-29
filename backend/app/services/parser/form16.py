"""Form 16 parser using Anthropic Claude with PDF input + tool-use.

The parser sends the entire PDF as a `document` content block and forces the model
to call `extract_form16` — a tool whose JSON schema mirrors `Form16Data`. That gives
us structured output without any regex post-processing.
"""

from __future__ import annotations

import base64
import logging

from anthropic import AsyncAnthropic
from anthropic import APIError, BadRequestError

from app.core.config import get_settings
from app.schemas.document import Form16Data

logger = logging.getLogger(__name__)


EXTRACTION_PROMPT = """\
You are a tax document parser. The PDF above is an Indian Form 16 (TDS certificate
issued by an employer for a salaried employee).

Extract every field you can see and call the `extract_form16` tool exactly once
with the structured data. Rules:

- Use Indian rupee values as numeric amounts (e.g. 1234567.89, no currency symbols
  or commas).
- For Chapter VI-A deductions and Section 10/16 line items, **always set the
  `section` field** with the exact IT Act section code as printed in the document
  (e.g. "80C", "80D", "80CCD(1B)", "10(13A)", "16(ia)", "16(iii)", "24(b)").
- If a field is not visible or not applicable, omit it (do not invent values).
- `ay` is the Assessment Year (e.g. "2026-27"); `fy` is the Financial Year
  (e.g. "2025-26").
- `regime` should be "old" or "new" if you can determine which tax regime was
  applied; otherwise omit it.
- TDS quarters: include exactly the quarters present in the document.
"""


# Tool schema mirrors Form16Data. Kept inline so the prompt + schema travel together.
FORM16_TOOL = {
    "name": "extract_form16",
    "description": "Submit the structured data extracted from the Form 16 PDF.",
    "input_schema": {
        "type": "object",
        "properties": {
            "ay": {"type": "string", "description": "Assessment year, e.g. '2026-27'"},
            "fy": {"type": "string", "description": "Financial year, e.g. '2025-26'"},
            "regime": {"type": "string", "enum": ["old", "new"]},
            "employer": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "tan": {"type": "string"},
                    "address": {"type": "string"},
                },
            },
            "employee": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "pan": {"type": "string"},
                },
            },
            "tds": {
                "type": "object",
                "properties": {
                    "quarters": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "quarter": {"type": "integer", "minimum": 1, "maximum": 4},
                                "amount_paid": {"type": "number"},
                                "tds_deducted": {"type": "number"},
                                "challan_no": {"type": "string"},
                                "date": {"type": "string", "description": "YYYY-MM-DD if available"},
                            },
                            "required": ["quarter"],
                        },
                    },
                    "total_tds": {"type": "number"},
                },
            },
            "salary": {
                "type": "object",
                "properties": {
                    "gross": {"type": "number"},
                    "components": {"type": "array", "items": {"$ref": "#/$defs/lineItem"}},
                    "section_10_exemptions": {"type": "array", "items": {"$ref": "#/$defs/lineItem"}},
                    "section_16": {"type": "array", "items": {"$ref": "#/$defs/lineItem"}},
                },
            },
            "chapter_vi_a": {"type": "array", "items": {"$ref": "#/$defs/lineItem"}},
            "taxable_income": {"type": "number"},
            "tax_payable": {"type": "number"},
        },
        "$defs": {
            "lineItem": {
                "type": "object",
                "properties": {
                    "section": {"type": "string"},
                    "label": {"type": "string"},
                    "amount": {"type": "number"},
                },
                "required": ["label", "amount"],
            }
        },
    },
}


class ParserConfigError(RuntimeError):
    pass


class ParserError(RuntimeError):
    pass


async def parse_form16(pdf_bytes: bytes) -> tuple[Form16Data, dict]:
    """Parse a Form 16 PDF and return (typed data, audit metadata)."""

    settings = get_settings()
    if not settings.anthropic_api_key:
        raise ParserConfigError(
            "ANTHROPIC_API_KEY is not set. Add it to backend/.env and restart the server."
        )

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("ascii")

    try:
        response = await client.messages.create(
            model=settings.parser_model,
            max_tokens=4096,
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
            tools=[FORM16_TOOL],
            tool_choice={"type": "tool", "name": "extract_form16"},
        )
    except BadRequestError as e:
        raise ParserError(f"Anthropic rejected the request: {e}") from e
    except APIError as e:
        raise ParserError(f"Anthropic API error: {e}") from e

    # Extract the tool_use block — there should be exactly one because of tool_choice.
    tool_block = next((b for b in response.content if b.type == "tool_use"), None)
    if tool_block is None:
        raise ParserError("Model did not return a tool_use block.")

    raw_input: dict = tool_block.input  # type: ignore[assignment]
    try:
        data = Form16Data.model_validate(raw_input)
    except Exception as e:
        logger.exception("Form16 schema validation failed", extra={"raw": raw_input})
        raise ParserError(f"Schema validation failed: {e}") from e

    audit = {
        "provider": "anthropic",
        "model": settings.parser_model,
        "stop_reason": response.stop_reason,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }
    return data, audit
