from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError
from app.core.config import settings
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.knowledge_document import KnowledgeDocument
from app.services.document_chunking import chunk_document_text
from app.services.document_extraction import (
    DocumentExtractionError,
    extract_text_from_document,
)
from app.services.embedding_service import (
    EmbeddingGenerationError,
    generate_embedding,
)


class KnowledgeDocumentNotFoundError(Exception):
    """Raised when a document does not belong to the requested organization."""

class DocumentAlreadyProcessingError(Exception):
    """Raised when another task is already processing this document."""

class DocumentProcessingError(Exception):
    """Raised when document processing fails."""


def resolve_document_path(file_path: str) -> Path:
    """Resolve a stored document path safely inside the storage directory."""

    storage_root = Path(settings.STORAGE_DIR).resolve()
    resolved_path = (storage_root / file_path).resolve()

    try:
        resolved_path.relative_to(storage_root)
    except ValueError as exc:
        raise DocumentProcessingError(
            "Invalid document storage path"
        ) from exc

    return resolved_path

def claim_document_for_processing(
    db: Session,
    document_id: UUID,
    organization_id: UUID,
) -> KnowledgeDocument:
    """Atomically claim a document so only one task processes it."""

    result = db.execute(
        update(KnowledgeDocument)
        .where(
            KnowledgeDocument.id == document_id,
            KnowledgeDocument.organization_id == organization_id,
            KnowledgeDocument.status != "processing",
        )
        .values(
            status="processing",
            error_message=None,
        )
        .execution_options(synchronize_session=False)
    )

    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise DocumentProcessingError(
            "Could not claim document for processing"
        ) from exc

    if result.rowcount != 1:
        db.rollback()

        document_exists = (
            db.query(KnowledgeDocument.id)
            .filter(
                KnowledgeDocument.id == document_id,
                KnowledgeDocument.organization_id == organization_id,
            )
            .first()
        )

        if document_exists is None:
            raise KnowledgeDocumentNotFoundError("Document not found")

        raise DocumentAlreadyProcessingError(
            "Document is already being processed"
        )

    return (
        db.query(KnowledgeDocument)
        .populate_existing()
        .filter(
            KnowledgeDocument.id == document_id,
            KnowledgeDocument.organization_id == organization_id,
        )
        .first()
    )

async def process_knowledge_document(
    db: Session,
    document_id: UUID,
    organization_id: UUID,
) -> KnowledgeDocument:
    """Extract, chunk, embed, and store a document's knowledge chunks."""

    document = claim_document_for_processing(
        db=db,
        document_id=document_id,
        organization_id=organization_id,
    )

    try:
        file_path = resolve_document_path(document.file_path)

        extracted_text = extract_text_from_document(
            file_path=file_path,
            content_type=document.content_type,
        )

        chunks = chunk_document_text(extracted_text)

        if not chunks:
            raise DocumentProcessingError(
                "No text chunks were generated from the document"
            )

        # Generate every embedding before inserting any chunks.
        embedded_chunks = []

        for chunk in chunks:
            embedding = await generate_embedding(chunk.content)

            embedded_chunks.append(
                {
                    "chunk": chunk,
                    "embedding": embedding,
                }
            )

        # Replace existing chunks only after all embeddings succeed.
        db.query(KnowledgeChunk).filter(
            KnowledgeChunk.document_id == document.id,
            KnowledgeChunk.organization_id == organization_id,
        ).delete(synchronize_session=False)

        for item in embedded_chunks:
            chunk = item["chunk"]

            db.add(
                KnowledgeChunk(
                    organization_id=organization_id,
                    document_id=document.id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    chunk_metadata={
                        "start_char": chunk.start_char,
                        "end_char": chunk.end_char,
                        "filename": document.filename,
                    },
                    embedding=item["embedding"],
                )
            )

        document.status = "completed"
        document.error_message = None

        # Save all chunks and the completed status atomically.
        db.commit()
        db.refresh(document)

        return document

    except Exception as exc:
        db.rollback()

        # Record failure separately so no partial chunk data is retained.
        failed_document = (
            db.query(KnowledgeDocument)
            .filter(
                KnowledgeDocument.id == document_id,
                KnowledgeDocument.organization_id == organization_id,
            )
            .first()
        )

        if failed_document is not None:
            failed_document.status = "failed"

            if isinstance(
                exc,
                (
                    DocumentExtractionError,
                    EmbeddingGenerationError,
                    DocumentProcessingError,
                ),
            ):
                failed_document.error_message = str(exc)[:2000]
            else:
                failed_document.error_message = (
                    "An unexpected error occurred during document processing"
                )

            db.commit()

        raise DocumentProcessingError(
            "Document processing failed"
        ) from exc