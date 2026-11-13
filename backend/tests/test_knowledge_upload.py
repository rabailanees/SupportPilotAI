from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.models.knowledge_document import KnowledgeDocument
from sqlalchemy.orm import sessionmaker

from app.api import knowledge as knowledge_api
from app.models.knowledge_chunk import KnowledgeChunk
from app.services import document_processing

def upload_document(client, organization_id, headers, filename, content):
    return client.post(
        f"/api/v1/organizations/{organization_id}/knowledge/documents/",
        headers=headers,
        files={
            "file": (filename, content, "application/octet-stream")
        },
    )

def test_upload_knowledge_document(
    client,
    tenant_context,
    db_session,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(settings, "STORAGE_DIR", tmp_path)

    # Give the background task its own session connected to the test DB.
    test_session_factory = sessionmaker(
        bind=db_session.get_bind(),
        autoflush=False,
        autocommit=False,
    )
    monkeypatch.setattr(
        knowledge_api,
        "SessionLocal",
        test_session_factory,
    )

    # Avoid calling the real Ollama service during this test.
    async def fake_generate_embedding(text):
        return [0.1] * 768

    monkeypatch.setattr(
        document_processing,
        "generate_embedding",
        fake_generate_embedding,
    )

    organization_id = str(tenant_context["organization_a"].id)

    response = upload_document(
        client,
        organization_id,
        tenant_context["headers_a"],
        "policy.txt",
        b"Company support policy.",
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["organization_id"] == organization_id
    assert data["filename"] == "policy.txt"
    assert data["content_type"] == "text/plain"
    assert data["status"] == "pending"
    assert data["id"]

    # The background task should have completed by this point.
    db_session.expire_all()

    document = db_session.scalar(
        select(KnowledgeDocument).where(
            KnowledgeDocument.id == data["id"]
        )
    )

    assert document is not None
    assert document.status == "completed"
    assert document.error_message is None

    stored_path = tmp_path / document.file_path

    assert stored_path.exists()
    assert stored_path.read_bytes() == b"Company support policy."

    chunks = db_session.scalars(
        select(KnowledgeChunk).where(
            KnowledgeChunk.document_id == document.id
        )
    ).all()

    assert len(chunks) == 1
    assert chunks[0].content == "Company support policy."
    assert len(chunks[0].embedding) == 768

def test_upload_requires_authentication(client, tenant_context, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_DIR", tmp_path)

    organization_id = str(tenant_context["organization_a"].id)

    response = upload_document(
        client,
        organization_id,
        {},
        "policy.txt",
        b"Company support policy.",
    )

    assert response.status_code == 401
    assert not list(tmp_path.rglob("*.txt"))


def test_user_cannot_upload_to_another_organization(
    client, tenant_context, tmp_path, monkeypatch
):
    monkeypatch.setattr(settings, "STORAGE_DIR", tmp_path)

    organization_b_id = str(tenant_context["organization_b"].id)

    response = upload_document(
        client,
        organization_b_id,
        tenant_context["headers_a"],
        "policy.txt",
        b"Unauthorized document.",
    )

    assert response.status_code == 404
    assert not list(tmp_path.rglob("*.txt"))


def test_upload_rejects_unsupported_file(
    client, tenant_context, tmp_path, monkeypatch
):
    monkeypatch.setattr(settings, "STORAGE_DIR", tmp_path)

    organization_id = str(tenant_context["organization_a"].id)

    response = upload_document(
        client,
        organization_id,
        tenant_context["headers_a"],
        "malware.exe",
        b"Some content",
    )

    assert response.status_code == 400
    assert not list(tmp_path.rglob("*.*"))


def test_upload_rejects_oversized_file(
    client, tenant_context, tmp_path, monkeypatch
):
    monkeypatch.setattr(settings, "STORAGE_DIR", tmp_path)
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_BYTES", 70_000)

    organization_id = str(tenant_context["organization_a"].id)

    response = upload_document(
        client,
        organization_id,
        tenant_context["headers_a"],
        "large.txt",
        b"a" * 80_000,
    )

    assert response.status_code == 413
    assert not list(tmp_path.rglob("*.txt"))


def test_upload_cleans_file_if_database_commit_fails(
    client, tenant_context, db_session, tmp_path, monkeypatch
):
    monkeypatch.setattr(settings, "STORAGE_DIR", tmp_path)

    def fail_commit():
        raise SQLAlchemyError("Simulated database failure")

    monkeypatch.setattr(db_session, "commit", fail_commit)

    organization_id = str(tenant_context["organization_a"].id)

    response = upload_document(
        client,
        organization_id,
        tenant_context["headers_a"],
        "policy.txt",
        b"Company support policy.",
    )

    assert response.status_code == 500
    assert not list(tmp_path.rglob("*.txt"))


def test_upload_marks_document_failed_when_processing_fails(
    client,
    tenant_context,
    db_session,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(settings, "STORAGE_DIR", tmp_path)

    # Ensure the background task uses the test database.
    test_session_factory = sessionmaker(
        bind=db_session.get_bind(),
        autoflush=False,
        autocommit=False,
    )
    monkeypatch.setattr(
        knowledge_api,
        "SessionLocal",
        test_session_factory,
    )

    def fail_extraction(**kwargs):
        raise document_processing.DocumentExtractionError(
            "Could not extract document text"
        )

    monkeypatch.setattr(
        document_processing,
        "extract_text_from_document",
        fail_extraction,
    )

    organization_id = str(tenant_context["organization_a"].id)

    response = upload_document(
        client,
        organization_id,
        tenant_context["headers_a"],
        "policy.txt",
        b"Company support policy.",
    )

    # Upload succeeds even though background processing fails.
    assert response.status_code == 201, response.text

    data = response.json()
    assert data["status"] == "pending"

    db_session.expire_all()

    document = db_session.scalar(
        select(KnowledgeDocument).where(
            KnowledgeDocument.id == data["id"]
        )
    )

    assert document is not None
    assert document.status == "failed"
    assert document.error_message == "Could not extract document text"

    chunks = db_session.scalars(
        select(KnowledgeChunk).where(
            KnowledgeChunk.document_id == document.id
        )
    ).all()

    assert chunks == []

    # Keep the original uploaded file for potential retry.
    assert (tmp_path / document.file_path).exists()
