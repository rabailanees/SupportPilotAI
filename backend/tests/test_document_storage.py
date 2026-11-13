import asyncio
from io import BytesIO
from uuid import uuid4

import pytest
from starlette.datastructures import UploadFile

from app.services.document_storage import (
    DocumentTooLargeError,
    DocumentUploadError,
    store_document_file,
)


def run_upload(filename, content, storage_dir, max_size=10 * 1024 * 1024):
    upload = UploadFile(
        file=BytesIO(content),
        filename=filename,
    )

    return asyncio.run(
        store_document_file(
            upload=upload,
            organization_id=uuid4(),
            storage_dir=storage_dir,
            max_size_bytes=max_size,
        )
    )


def test_store_valid_text_file(tmp_path):
    content = b"Company support policy."

    result = run_upload(
        "policy.txt",
        content,
        tmp_path,
    )

    stored_path = tmp_path / result.storage_key

    assert result.filename == "policy.txt"
    assert result.content_type == "text/plain"
    assert result.size_bytes == len(content)
    assert stored_path.read_bytes() == content


def test_store_valid_pdf_file(tmp_path):
    content = b"%PDF-1.7\nTest PDF content"

    result = run_upload(
        "manual.pdf",
        content,
        tmp_path,
    )

    stored_path = tmp_path / result.storage_key

    assert result.filename == "manual.pdf"
    assert result.content_type == "application/pdf"
    assert stored_path.read_bytes() == content


def test_reject_unsupported_extension(tmp_path):
    with pytest.raises(DocumentUploadError):
        run_upload(
            "malware.exe",
            b"some content",
            tmp_path,
        )


def test_reject_invalid_pdf_content(tmp_path):
    with pytest.raises(DocumentUploadError):
        run_upload(
            "fake.pdf",
            b"This is not a PDF",
            tmp_path,
        )


def test_reject_invalid_utf8_text(tmp_path):
    with pytest.raises(DocumentUploadError):
        run_upload(
            "invalid.txt",
            b"\xff\xfe\xfa",
            tmp_path,
        )


def test_reject_empty_file(tmp_path):
    with pytest.raises(DocumentUploadError):
        run_upload(
            "empty.txt",
            b"",
            tmp_path,
        )


def test_reject_oversized_file_and_remove_partial_file(tmp_path):
    content = b"a" * 65_536 + b"b" * 10_000

    with pytest.raises(DocumentTooLargeError):
        run_upload(
            "large.txt",
            content,
            tmp_path,
            max_size=70_000,
        )

    stored_files = list(tmp_path.rglob("*"))

    assert not [path for path in stored_files if path.is_file()]
