from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.conversation import Conversation
from app.models.user import User
from app.schemas.conversation import ConversationCreate, ConversationResponse


router = APIRouter(
    prefix="/organizations/{organization_id}/conversations",
    tags=["Conversations"],
)


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
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    organization_id: UUID,
    payload: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_organization_access(organization_id, current_user)

    conversation = Conversation(
        organization_id=current_user.organization_id,
        customer_email=str(payload.customer_email).lower(),
    )

    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return conversation


@router.get(
    "/",
    response_model=list[ConversationResponse],
)
def list_conversations(
    organization_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_organization_access(organization_id, current_user)

    statement = (
        select(Conversation)
        .where(
            Conversation.organization_id == current_user.organization_id
        )
        .order_by(Conversation.created_at.desc())
    )

    return db.scalars(statement).all()
