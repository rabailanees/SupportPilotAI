import pytest
from pypdf import PdfWriter

from app.services.document_extraction import (
    DocumentExtractionError,
    extract_text_from_document,
)

def create_text_pdf(path):
    content = b"BT /F1 12 Tf 50 250 Td (Test PDF content) Tj ET"

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R "
            b"/MediaBox [0 0 300 300] "
            b"/Resources << /Font << /F1 4 0 R >> >> "
            b"/Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        (
            b"<< /Length " + str(len(content)).encode()
            + b" >>\nstream\n" + content + b"\nendstream"
        ),
    ]

    pdf = b"%PDF-1.4\n"
    offsets = [0]

    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += f"{index} 0 obj\n".encode() + obj + b"\nendobj\n"

    xref_offset = len(pdf)

    pdf += f"xref\n0 {len(objects) + 1}\n".encode()
    pdf += b"0000000000 65535 f \n"

    for offset in offsets[1:]:
        pdf += f"{offset:010d} 00000 n \n".encode()

    pdf += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode()

    path.write_bytes(pdf)

def test_extract_text_from_pdf(tmp_path):
    file_path = tmp_path / "manual.pdf"
    create_text_pdf(file_path)

    result = extract_text_from_document(
        file_path,
        "application/pdf",
    )

    assert result == "Test PDF content"

def test_extract_text_file(tmp_path):
    file_path = tmp_path / "policy.txt"
    file_path.write_text(
        "Company support policy.",
        encoding="utf-8",
    )

    result = extract_text_from_document(
        file_path,
        "text/plain",
    )

    assert result == "Company support policy."


def test_extract_pdf_without_extractable_text(tmp_path):
    file_path = tmp_path / "empty.pdf"

    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)

    with file_path.open("wb") as file:
        writer.write(file)

    with pytest.raises(
        DocumentExtractionError,
        match="No extractable text",
    ):
        extract_text_from_document(
            file_path,
            "application/pdf",
        )


def test_reject_missing_file(tmp_path):
    with pytest.raises(
        DocumentExtractionError,
        match="Document file not found",
    ):
        extract_text_from_document(
            tmp_path / "missing.txt",
            "text/plain",
        )


def test_reject_unsupported_content_type(tmp_path):
    file_path = tmp_path / "document.txt"
    file_path.write_text("Some content", encoding="utf-8")

    with pytest.raises(
        DocumentExtractionError,
        match="Unsupported document content type",
    ):
        extract_text_from_document(
            file_path,
            "application/octet-stream",
        )


def test_reject_invalid_pdf(tmp_path):
    file_path = tmp_path / "invalid.pdf"
    file_path.write_bytes(b"This is not a valid PDF")

    with pytest.raises(
        DocumentExtractionError,
        match="Could not extract text",
    ):
        extract_text_from_document(
            file_path,
            "application/pdf",
        )