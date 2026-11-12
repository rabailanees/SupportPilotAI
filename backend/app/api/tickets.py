from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.conversation import Conversation
from app.models.support_ticket import SupportTicket
from app.models.user import User
from app.schemas.ticket import (
    TicketCreate,
    TicketUpdate,
    TicketResponse,
)


router = APIRouter(
    prefix="/organizations/{organization_id}/tickets",
    tags=["Tickets"],
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
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_ticket(
    organization_id: UUID,
    payload: TicketCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_organization_access(organization_id, current_user)

    if payload.conversation_id is not None:
        conversation_statement = select(Conversation).where(
            Conversation.id == payload.conversation_id,
            Conversation.organization_id == current_user.organization_id,
        )

        conversation = db.scalar(conversation_statement)

        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )

    ticket = SupportTicket(
        organization_id=current_user.organization_id,
        conversation_id=payload.conversation_id,
        customer_email=str(payload.customer_email).lower(),
        subject=payload.subject,
        description=payload.description,
        priority=payload.priority,
    )

    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    return ticket


@router.get("/", response_model=list[TicketResponse])
def list_tickets(
    organization_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_organization_access(organization_id, current_user)

    statement = (
        select(SupportTicket)
        .where(
            SupportTicket.organization_id == current_user.organization_id
        )
        .order_by(SupportTicket.created_at.desc())
    )

    return db.scalars(statement).all()


@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(
    organization_id: UUID,
    ticket_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_organization_access(organization_id, current_user)

    statement = select(SupportTicket).where(
        SupportTicket.id == ticket_id,
        SupportTicket.organization_id == current_user.organization_id,
    )

    ticket = db.scalar(statement)

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    return ticket


@router.patch("/{ticket_id}", response_model=TicketResponse)
def update_ticket(
    organization_id: UUID,
    ticket_id: UUID,
    payload: TicketUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verify_organization_access(organization_id, current_user)

    statement = select(SupportTicket).where(
        SupportTicket.id == ticket_id,
        SupportTicket.organization_id == current_user.organization_id,
    )

    ticket = db.scalar(statement)

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    updates = payload.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one field to update",
        )

    if any(value is None for value in updates.values()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Status and priority cannot be null",
        )

    for field, value in updates.items():
        setattr(ticket, field, value)

    db.commit()
    db.refresh(ticket)

    return ticket
