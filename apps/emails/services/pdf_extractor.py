"""PDF text extraction service using pypdf (BSD license).

Extracts text from the first N pages of a PDF, truncated to max_chars.
Returns empty string on any error (corrupt PDF, oversized file, etc.).

Design decision: pypdf instead of PyMuPDF (AGPL) -- see STATE.md.
"""

import logging
from io import BytesIO

logger = logging.getLogger(__name__)

# Maximum PDF file size to process (5 MB)
MAX_PDF_SIZE = 5 * 1024 * 1024


def extract_pdf_text(
    pdf_bytes: bytes, max_pages: int = 3, max_chars: int = 1000
) -> str:
    """Extract text from a PDF byte stream.

    Args:
        pdf_bytes: Raw PDF file bytes.
        max_pages: Maximum number of pages to read (default 3).
        max_chars: Maximum characters to return (default 1000).

    Returns:
        Extracted text, truncated if needed. Empty string on any error.
    """
    if not pdf_bytes:
        return ""

    if len(pdf_bytes) > MAX_PDF_SIZE:
        logger.info(f"PDF skipped: {len(pdf_bytes)} bytes exceeds {MAX_PDF_SIZE} limit")
        return ""

    try:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(pdf_bytes))
        text_parts = []
        for page_num in range(min(len(reader.pages), max_pages)):
            page_text = reader.pages[page_num].extract_text() or ""
            text_parts.append(page_text)

        full_text = "\n".join(text_parts).strip()

        if len(full_text) > max_chars:
            full_text = full_text[:max_chars] + "[...truncated...]"

        return full_text

    except Exception as e:
        logger.warning(f"PDF extraction failed: {e}")
        return ""
