import logging
from uuid import UUID
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.db.session import SessionLocal, get_db
from app.models.knowledge_document import KnowledgeDocument
from app.models.user import User
from app.schemas.knowledge import KnowledgeDocumentResponse
from app.services.document_processing import process_knowledge_document
from app.services.document_storage import (
    DocumentTooLargeError,
    DocumentUploadError,
    store_document_file,
)

router = APIRouter(
    prefix="/organizations/{organization_id}/knowledge/documents",
    tags=["Knowledge Base"],
)

logger = logging.getLogger(__name__)


async def process_document_in_background(
    document_id: UUID,
    organization_id: UUID,
):
    """Process an uploaded document using an independent database session."""

    db = SessionLocal()

    try:
        await process_knowledge_document(
            db=db,
            document_id=document_id,
            organization_id=organization_id,
        )

    except Exception:
        logger.exception(
            "Background processing failed for document %s",
            document_id,
        )

    finally:
        db.close()


def verify_organization_access(
    organization_id: UUID,
    current_user: User,
):
    if organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )


@router.post(
    "/",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_knowledge_document(
    organization_id: UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_organization_access(organization_id, current_user)

    try:
        stored_file = await store_document_file(
            upload=file,
            organization_id=organization_id,
            storage_dir=settings.STORAGE_DIR,
            max_size_bytes=settings.MAX_UPLOAD_SIZE_BYTES,
        )

    except DocumentTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        ) from exc

    except DocumentUploadError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    document = KnowledgeDocument(
        organization_id=organization_id,
        filename=stored_file.filename,
        content_type=stored_file.content_type,
        file_path=stored_file.storage_key,
        status="pending",
    )

    db.add(document)

    try:
        db.commit()

    except SQLAlchemyError as exc:
        db.rollback()

        stored_path = settings.STORAGE_DIR / stored_file.storage_key
        stored_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save document record",
        ) from exc

    db.refresh(document)

    background_tasks.add_task(
        process_document_in_background,
        document.id,
        organization_id,
    )

    return document