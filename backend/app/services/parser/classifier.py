"""Document classifier — figures out doc_type by scanning extracted text.

We deliberately keep this rule-based: it's free, deterministic, fast, and reliable
for the common Indian tax-document layouts. Handles both PDF (Form 16, CAS) and
XLSX (broker tax P&L from Zerodha/Groww/etc.). A scanned PDF (text extraction
empty) falls through to 'unknown' and the user is asked to upload a text-based
version.
"""

from __future__ import annotations

import logging
import re
from io import BytesIO
from typing import Literal

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.services.parser.xlsx import is_xlsx, xlsx_to_text

logger = logging.getLogger(__name__)

DocType = Literal["form16", "capital_gains", "unknown"]


# Patterns that strongly indicate a Form 16 (TDS certificate)
FORM16_PATTERNS = [
    re.compile(r"\bform\s*no\.?\s*16\b", re.IGNORECASE),
    re.compile(r"\bform\s+16\b", re.IGNORECASE),
    re.compile(r"certificate\s+under\s+section\s+203", re.IGNORECASE),
    re.compile(r"deduction\s+of\s+tax\s+at\s+source", re.IGNORECASE),
    re.compile(r"\btds\s+certificate\b", re.IGNORECASE),
]

# Patterns that strongly indicate a capital gains / broker tax statement.
# Indian broker XLSX exports use a wide vocabulary — Zerodha says "Tradewise
# Profit and Loss", Groww says "Capital Gains Statement", others say
# "Realised Gain" / "Realised Profit". Be permissive.
CAPITAL_GAINS_PATTERNS = [
    re.compile(r"\bcapital\s+gains?\b", re.IGNORECASE),
    re.compile(r"short[-\s]?term\s+capital\s+gain", re.IGNORECASE),
    re.compile(r"long[-\s]?term\s+capital\s+gain", re.IGNORECASE),
    re.compile(r"\bSTCG\b"),
    re.compile(r"\bLTCG\b"),
    re.compile(r"\btax\s*p\s*[&/]\s*l\b", re.IGNORECASE),
    re.compile(r"\bp\s*[&/]\s*l\s+statement\b", re.IGNORECASE),
    re.compile(r"tradewise\s+profit\s+and\s+loss", re.IGNORECASE),
    re.compile(r"realis[eq]d\s+(profit|gain|loss)", re.IGNORECASE),
    re.compile(r"unrealis[eq]d\s+(profit|gain|loss)", re.IGNORECASE),
    re.compile(r"\btradebook\b", re.IGNORECASE),
    re.compile(r"\bholdings?\s+statement\b", re.IGNORECASE),
    re.compile(r"\bequity\s+mutual\s+fund\b", re.IGNORECASE),
    re.compile(r"\bconsolidated\s+account\s+statement\b", re.IGNORECASE),
    re.compile(r"\bcams\b", re.IGNORECASE),
    re.compile(r"\bkfintech\b", re.IGNORECASE),
    re.compile(r"\bkarvy\b", re.IGNORECASE),
    re.compile(r"\bbuy\s+date\b.*\bsell\s+date\b", re.IGNORECASE | re.DOTALL),
    re.compile(r"\bisin\b.*\bquantity\b", re.IGNORECASE | re.DOTALL),
]

# Known broker names — soft signal that bumps capital_gains confidence
KNOWN_BROKERS = re.compile(
    r"\b(zerodha|kite|console|groww|nextbillion|upstox|angel\s*one|angel\s*broking|"
    r"5paisa|icici\s*direct|hdfc\s*securities|kotak\s*securities|sharekhan|"
    r"motilal\s*oswal|paytm\s*money|dhan|fyers|smallcase)\b",
    re.IGNORECASE,
)

# Phrases that strongly suggest "this is a financial statement of some kind"
FINANCIAL_HINTS = re.compile(
    r"\b(profit|loss|gain|p\s*[&/]\s*l|equity|mutual\s+fund|f\s*&\s*o|"
    r"futures|options|isin|symbol|trade|broker|portfolio|holdings)\b",
    re.IGNORECASE,
)


def _extract_first_page_text(pdf_bytes: bytes, max_pages: int = 2) -> str:
    """Pull text from the first 1–2 pages of an unencrypted PDF."""

    try:
        reader = PdfReader(BytesIO(pdf_bytes))
    except PdfReadError:
        return ""
    if reader.is_encrypted:
        return ""
    text_parts: list[str] = []
    for page in reader.pages[:max_pages]:
        try:
            text_parts.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(text_parts)


def classify(content: bytes) -> DocType:
    """Return 'form16' | 'capital_gains' | 'unknown' based on extracted text.

    Auto-detects PDF vs XLSX by magic bytes.
    """

    text = _extract_text(content)
    if not text.strip():
        return "unknown"
    return _classify_text(text)


def _extract_text(content: bytes) -> str:
    """Get text out of either a PDF or XLSX file. Returns '' if encrypted/unparseable."""
    if is_xlsx(content):
        try:
            return xlsx_to_text(content)
        except ValueError:
            return ""
    return _extract_first_page_text(content)


def _classify_text(text: str) -> DocType:
    form16_hits = sum(1 for p in FORM16_PATTERNS if p.search(text))
    cg_hits = sum(1 for p in CAPITAL_GAINS_PATTERNS if p.search(text))
    has_broker = bool(KNOWN_BROKERS.search(text))
    has_finance = bool(FINANCIAL_HINTS.search(text))

    # Form 16 is unambiguous when its patterns match — they're very specific.
    if form16_hits >= 1:
        return "form16"

    # Capital gains: any direct phrase, OR a broker name + any financial hint.
    if cg_hits >= 1:
        return "capital_gains"
    if has_broker and has_finance:
        return "capital_gains"

    # Final fallback: log the first chunk of text so we can iterate on patterns.
    sample = text[:600].replace("\n", " ⏎ ")
    logger.info("Classifier returned 'unknown'. First 600 chars: %s", sample)
    return "unknown"
