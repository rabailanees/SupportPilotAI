from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.schemas.message import MessageCreate, MessageResponse


router = APIRouter(
    prefix="/conversations/{conversation_id}/messages",
    tags=["Messages"],
)


def get_tenant_conversation(
    conversation_id: UUID,
    current_user: User,
    db: Session,
) -> Conversation:
    statement = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.organization_id == current_user.organization_id,
    )

    conversation = db.scalar(statement)

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    return conversation


@router.post(
    "/",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_message(
    conversation_id: UUID,
    payload: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = get_tenant_conversation(
        conversation_id,
        current_user,
        db,
    )

    message = Message(
        conversation_id=conversation.id,
        sender_type=payload.sender_type,
        content=payload.content,
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return message


@router.get(
    "/",
    response_model=list[MessageResponse],
)
def list_messages(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_tenant_conversation(conversation_id, current_user, db)

    statement = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )

    return db.scalars(statement).all()
