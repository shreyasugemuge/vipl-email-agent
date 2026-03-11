"""Tests for PDF text extraction service."""

import pytest

from apps.emails.services.pdf_extractor import extract_pdf_text


def _make_simple_pdf(text="Hello World. This is a test PDF document.", num_pages=1):
    """Create a simple PDF with pypdf for testing."""
    from pypdf import PdfWriter
    from pypdf.generic import (
        ArrayObject,
        DictionaryObject,
        NameObject,
        NumberObject,
        TextStringObject,
        StreamObject,
    )
    import io

    writer = PdfWriter()
    for _ in range(num_pages):
        # Create a minimal page with text content
        page = writer.add_blank_page(width=612, height=792)

        # Create a content stream that draws text
        content = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET"

        # Build a proper content stream
        stream = StreamObject()
        stream._data = content.encode("latin-1")

        # Add a font resource
        font_dict = DictionaryObject()
        font_dict[NameObject("/Type")] = NameObject("/Font")
        font_dict[NameObject("/Subtype")] = NameObject("/Type1")
        font_dict[NameObject("/BaseFont")] = NameObject("/Helvetica")

        fonts = DictionaryObject()
        fonts[NameObject("/F1")] = font_dict

        resources = DictionaryObject()
        resources[NameObject("/Font")] = fonts

        page[NameObject("/Resources")] = resources
        page[NameObject("/Contents")] = writer._add_object(stream)

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


class TestPdfExtractor:
    """Test PDF text extraction."""

    def test_extract_valid_pdf(self):
        pdf_bytes = _make_simple_pdf("Test content for extraction")
        result = extract_pdf_text(pdf_bytes)
        assert "Test content for extraction" in result

    def test_extract_truncates_at_max_chars(self):
        long_text = "A" * 200
        pdf_bytes = _make_simple_pdf(long_text)
        result = extract_pdf_text(pdf_bytes, max_chars=50)
        assert len(result) <= 50 + len("[...truncated...]")
        if len(result) > 50:
            assert result.endswith("[...truncated...]")

    def test_extract_corrupt_pdf_returns_empty_string(self):
        result = extract_pdf_text(b"this is not a valid pdf")
        assert result == ""

    def test_extract_oversized_pdf_skipped(self):
        # 5 MB + 1 byte -- should be skipped
        big_bytes = b"x" * (5 * 1024 * 1024 + 1)
        result = extract_pdf_text(big_bytes)
        assert result == ""

    def test_extract_empty_bytes_returns_empty(self):
        result = extract_pdf_text(b"")
        assert result == ""
