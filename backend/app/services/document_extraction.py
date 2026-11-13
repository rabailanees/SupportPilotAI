from pathlib import Path

from pypdf import PdfReader


class DocumentExtractionError(Exception):
    """Raised when document text cannot be extracted."""


def extract_text_from_document(
    file_path: Path,
    content_type: str,
) -> str:
    if not file_path.exists() or not file_path.is_file():
        raise DocumentExtractionError("Document file not found")

    try:
        if content_type == "text/plain":
            text = file_path.read_text(encoding="utf-8")

        elif content_type == "application/pdf":
            reader = PdfReader(str(file_path))

            if reader.is_encrypted:
                raise DocumentExtractionError(
                    "Password-protected PDFs are not supported"
                )

            extracted_pages = []

            for page in reader.pages:
                page_text = page.extract_text()

                if page_text:
                    extracted_pages.append(page_text)

            text = "\n\n".join(extracted_pages)

        else:
            raise DocumentExtractionError(
                "Unsupported document content type"
            )

    except DocumentExtractionError:
        raise

    except Exception as exc:
        raise DocumentExtractionError(
            "Could not extract text from document"
        ) from exc

    text = text.strip()

    if not text:
        raise DocumentExtractionError(
            "No extractable text found in document. "
            "The PDF may contain scanned images and require OCR."
        )

    return text