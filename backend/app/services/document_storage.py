from codecs import getincrementaldecoder
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile


CHUNK_SIZE = 64 * 1024

SUPPORTED_TYPES = {
    ".txt": "text/plain",
    ".pdf": "application/pdf",
}


class DocumentUploadError(Exception):
    """Raised when an uploaded document is invalid."""


class DocumentTooLargeError(DocumentUploadError):
    """Raised when an uploaded document exceeds the size limit."""


@dataclass(frozen=True)
class StoredDocumentFile:
    filename: str
    content_type: str
    storage_key: str
    size_bytes: int


async def store_document_file(
    upload: UploadFile,
    organization_id: UUID,
    storage_dir: Path,
    max_size_bytes: int,
) -> StoredDocumentFile:

    raw_filename = upload.filename or ""

    # Remove any directory information supplied by the client.
    filename = raw_filename.replace("\\", "/").rsplit("/", 1)[-1].strip()

    if (
        not filename
        or len(filename) > 255
        or any(ord(char) < 32 for char in filename)
    ):
        raise DocumentUploadError("Invalid filename")

    extension = Path(filename).suffix.lower()
    content_type = SUPPORTED_TYPES.get(extension)

    if content_type is None:
        raise DocumentUploadError(
            "Only PDF and TXT files are supported"
        )

    first_chunk = await upload.read(CHUNK_SIZE)

    if not first_chunk:
        raise DocumentUploadError("Empty files are not allowed")

    if len(first_chunk) > max_size_bytes:
        raise DocumentTooLargeError("File exceeds the 10 MB limit")

    # Validate the actual file content, not the client MIME header.
    decoder = None

    if extension == ".pdf":
        if not first_chunk.startswith(b"%PDF-"):
            raise DocumentUploadError("Invalid PDF file")
    else:
        decoder = getincrementaldecoder("utf-8")("strict")

        try:
            decoder.decode(first_chunk, final=False)
        except UnicodeDecodeError as exc:
            raise DocumentUploadError(
                "TXT files must contain valid UTF-8 text"
            ) from exc

    organization_dir = storage_dir / "knowledge" / str(organization_id)
    organization_dir.mkdir(parents=True, exist_ok=True)

    stored_filename = f"{uuid4()}{extension}"
    destination = organization_dir / stored_filename

    size_bytes = len(first_chunk)

    try:
        with destination.open("xb") as file:
            file.write(first_chunk)

            while True:
                chunk = await upload.read(CHUNK_SIZE)

                if not chunk:
                    break

                size_bytes += len(chunk)

                if size_bytes > max_size_bytes:
                    raise DocumentTooLargeError(
                        "File exceeds the 10 MB limit"
                    )

                if decoder is not None:
                    decoder.decode(chunk, final=False)

                file.write(chunk)

            if decoder is not None:
                decoder.decode(b"", final=True)

    except UnicodeDecodeError as exc:
        destination.unlink(missing_ok=True)
        raise DocumentUploadError(
            "TXT files must contain valid UTF-8 text"
        ) from exc

    except Exception:
        destination.unlink(missing_ok=True)
        raise

    return StoredDocumentFile(
        filename=filename,
        content_type=content_type,
        storage_key=f"knowledge/{organization_id}/{stored_filename}",
        size_bytes=size_bytes,
    )
