import pytest
from sqlalchemy.exc import IntegrityError

from app.models.knowledge_document import KnowledgeDocument
from app.models.knowledge_chunk import KnowledgeChunk


def create_document(db_session, organization_id):
    document = KnowledgeDocument(
        organization_id=organization_id,
        filename="company-policy.txt",
        content_type="text/plain",
        file_path="uploads/company-policy.txt",
    )
    db_session.add(document)
    db_session.flush()
    return document


def test_organization_can_create_own_knowledge_chunk(
    db_session,
    tenant_context,
):
    organization = tenant_context["organization_a"]

    document = create_document(db_session, organization.id)

    chunk = KnowledgeChunk(
        organization_id=organization.id,
        document_id=document.id,
        chunk_index=0,
        content="Employees receive annual leave.",
    )

    db_session.add(chunk)
    db_session.flush()

    assert chunk.id is not None
    assert chunk.document_id == document.id


def test_organization_cannot_create_chunk_for_another_organizations_document(
    db_session,
    tenant_context,
):
    organization_a = tenant_context["organization_a"]
    organization_b = tenant_context["organization_b"]

    document = create_document(db_session, organization_a.id)

    invalid_chunk = KnowledgeChunk(
        organization_id=organization_b.id,
        document_id=document.id,
        chunk_index=0,
        content="This should be rejected.",
    )

    db_session.add(invalid_chunk)

    with pytest.raises(IntegrityError):
        db_session.flush()
