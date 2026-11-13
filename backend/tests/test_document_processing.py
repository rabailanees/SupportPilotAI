import asyncio

import pytest

from app.models.knowledge_chunk import KnowledgeChunk
from app.models.knowledge_document import KnowledgeDocument
from app.services import document_processing
from app.services.document_processing import (
    DocumentAlreadyProcessingError,
    DocumentProcessingError,
    KnowledgeDocumentNotFoundError,
    claim_document_for_processing,
    process_knowledge_document,
)
from app.services.embedding_service import EmbeddingGenerationError


def create_document(db_session, organization_id):
    document = KnowledgeDocument(
        organization_id=organization_id,
        filename="company-policy.txt",
        content_type="text/plain",
        file_path=f"knowledge/{organization_id}/company-policy.txt",
        status="pending",
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)
    return document


def test_process_document_success(
    db_session,
    tenant_context,
    monkeypatch,
):
    organization = tenant_context["organization_a"]
    document = create_document(db_session, organization.id)

    extracted_text = (
        "Employees receive annual leave. "
        "Employees must submit leave requests to their manager. "
    ) * 30

    monkeypatch.setattr(
        document_processing,
        "extract_text_from_document",
        lambda **kwargs: extracted_text,
    )

    async def fake_generate_embedding(text):
        return [0.1] * 768

    monkeypatch.setattr(
        document_processing,
        "generate_embedding",
        fake_generate_embedding,
    )

    result = asyncio.run(
        process_knowledge_document(
            db=db_session,
            document_id=document.id,
            organization_id=organization.id,
        )
    )

    db_session.refresh(result)

    chunks = (
        db_session.query(KnowledgeChunk)
        .filter(
            KnowledgeChunk.document_id == document.id,
            KnowledgeChunk.organization_id == organization.id,
        )
        .order_by(KnowledgeChunk.chunk_index)
        .all()
    )

    assert result.status == "completed"
    assert result.error_message is None
    assert len(chunks) > 0

    assert [chunk.chunk_index for chunk in chunks] == list(
        range(len(chunks))
    )

    for chunk in chunks:
        assert len(chunk.embedding) == 768
        assert chunk.content
        assert "start_char" in chunk.chunk_metadata
        assert "end_char" in chunk.chunk_metadata
        assert chunk.chunk_metadata["filename"] == document.filename


def test_process_document_rejects_another_organizations_document(
    db_session,
    tenant_context,
):
    organization_a = tenant_context["organization_a"]
    organization_b = tenant_context["organization_b"]

    document = create_document(db_session, organization_a.id)

    with pytest.raises(KnowledgeDocumentNotFoundError):
        asyncio.run(
            process_knowledge_document(
                db=db_session,
                document_id=document.id,
                organization_id=organization_b.id,
            )
        )

    db_session.refresh(document)
    assert document.status == "pending"


def test_extraction_failure_marks_document_failed(
    db_session,
    tenant_context,
    monkeypatch,
):
    organization = tenant_context["organization_a"]
    document = create_document(db_session, organization.id)

    def fail_extraction(**kwargs):
        raise document_processing.DocumentExtractionError(
            "Could not extract document text"
        )

    monkeypatch.setattr(
        document_processing,
        "extract_text_from_document",
        fail_extraction,
    )

    with pytest.raises(DocumentProcessingError):
        asyncio.run(
            process_knowledge_document(
                db=db_session,
                document_id=document.id,
                organization_id=organization.id,
            )
        )

    db_session.refresh(document)

    chunks = (
        db_session.query(KnowledgeChunk)
        .filter(KnowledgeChunk.document_id == document.id)
        .all()
    )

    assert document.status == "failed"
    assert document.error_message == "Could not extract document text"
    assert chunks == []


def test_embedding_failure_does_not_save_partial_chunks(
    db_session,
    tenant_context,
    monkeypatch,
):
    organization = tenant_context["organization_a"]
    document = create_document(db_session, organization.id)

    extracted_text = "This is a company policy sentence. " * 150

    monkeypatch.setattr(
        document_processing,
        "extract_text_from_document",
        lambda **kwargs: extracted_text,
    )

    call_count = 0

    async def fail_embedding(text):
        nonlocal call_count
        call_count += 1

        if call_count == 2:
            raise EmbeddingGenerationError("Ollama unavailable")

        return [0.1] * 768

    monkeypatch.setattr(
        document_processing,
        "generate_embedding",
        fail_embedding,
    )

    with pytest.raises(DocumentProcessingError):
        asyncio.run(
            process_knowledge_document(
                db=db_session,
                document_id=document.id,
                organization_id=organization.id,
            )
        )

    db_session.refresh(document)

    chunks = (
        db_session.query(KnowledgeChunk)
        .filter(KnowledgeChunk.document_id == document.id)
        .all()
    )

    assert call_count == 2
    assert document.status == "failed"
    assert document.error_message == "Ollama unavailable"
    assert chunks == []


def test_reprocessing_replaces_existing_chunks(
    db_session,
    tenant_context,
    monkeypatch,
):
    organization = tenant_context["organization_a"]
    document = create_document(db_session, organization.id)

    current_text = {
        "value": "Original company policy. " * 100
    }

    monkeypatch.setattr(
        document_processing,
        "extract_text_from_document",
        lambda **kwargs: current_text["value"],
    )

    async def fake_generate_embedding(text):
        return [0.1] * 768

    monkeypatch.setattr(
        document_processing,
        "generate_embedding",
        fake_generate_embedding,
    )

    # First processing run.
    asyncio.run(
        process_knowledge_document(
            db=db_session,
            document_id=document.id,
            organization_id=organization.id,
        )
    )

    first_chunks = (
        db_session.query(KnowledgeChunk)
        .filter(KnowledgeChunk.document_id == document.id)
        .all()
    )

    first_count = len(first_chunks)
    assert first_count > 0

    # Change the extracted content and process the same document again.
    current_text["value"] = "Updated company policy. " * 100

    asyncio.run(
        process_knowledge_document(
            db=db_session,
            document_id=document.id,
            organization_id=organization.id,
        )
    )

    second_chunks = (
        db_session.query(KnowledgeChunk)
        .filter(KnowledgeChunk.document_id == document.id)
        .all()
    )

    assert len(second_chunks) == first_count
    assert second_chunks[0].content.startswith(
        "Updated company policy."
    )

    assert all(
        "Original company policy." not in chunk.content
        for chunk in second_chunks
    )

    assert any(
        "Updated company policy." in chunk.content
        for chunk in second_chunks
    )

    db_session.refresh(document)
    assert document.status == "completed"

def test_document_cannot_be_claimed_twice(
    db_session,
    tenant_context,
):
    organization = tenant_context["organization_a"]
    document = create_document(db_session, organization.id)

    # First task successfully claims the document.
    claimed_document = claim_document_for_processing(
        db=db_session,
        document_id=document.id,
        organization_id=organization.id,
    )

    assert claimed_document.status == "processing"

    # A second task must not claim the same document.
    with pytest.raises(DocumentAlreadyProcessingError):
        claim_document_for_processing(
            db=db_session,
            document_id=document.id,
            organization_id=organization.id,
        )

    db_session.refresh(document)
    assert document.status == "processing"


@pytest.mark.parametrize("previous_status", ["completed", "failed"])
def test_completed_or_failed_document_can_be_claimed_again(
    db_session,
    tenant_context,
    previous_status,
):
    organization = tenant_context["organization_a"]
    document = create_document(db_session, organization.id)

    document.status = previous_status
    db_session.commit()

    claimed_document = claim_document_for_processing(
        db=db_session,
        document_id=document.id,
        organization_id=organization.id,
    )

    assert claimed_document.status == "processing"
    assert claimed_document.error_message is None