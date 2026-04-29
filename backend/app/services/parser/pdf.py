"""PDF utilities — encryption detection + password decryption.

Most Indian Form 16 PDFs are password-protected. The standard format is
`PAN[:5] + DOB(DDMMYYYY)`, but here we just take whatever the user provides.
"""

from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError


def is_encrypted(pdf_bytes: bytes) -> bool:
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
    except PdfReadError as e:
        # If we can't even open the PDF, treat it as not-our-problem here;
        # the parser will surface a meaningful error.
        raise ValueError(f"Could not read PDF: {e}") from e
    return bool(reader.is_encrypted)


def decrypt_pdf(pdf_bytes: bytes, password: str) -> bytes:
    """Return decrypted PDF bytes. Raises ValueError on wrong password.

    If the PDF is not actually encrypted, returns the input unchanged.
    """

    reader = PdfReader(BytesIO(pdf_bytes))
    if not reader.is_encrypted:
        return pdf_bytes

    # PdfReader.decrypt returns 0 on failure, 1 if decrypted with user password,
    # 2 if decrypted with owner password.
    result = reader.decrypt(password)
    if result == 0:
        raise ValueError("Incorrect password")

    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    out = BytesIO()
    writer.write(out)
    return out.getvalue()
