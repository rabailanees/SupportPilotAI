
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.organization import Organization
from app.models.conversation import Conversation
from app.models.support_ticket import SupportTicket
from app.schemas.ticket import (
    TicketCreate,
    TicketUpdate,
    TicketResponse,
)

router = APIRouter(
    prefix="/organizations/{organization_id}/tickets",
    tags=["Tickets"],
)


@router.post(
    "/",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_ticket(
    organization_id: UUID,
    payload: TicketCreate,
    db: Session = Depends(get_db),
):
    organization = db.get(Organization, organization_id)

    if not organization:
        raise HTTPException(
            status_code=404,
            detail="Organization not found",
        )

    if payload.conversation_id:
        conversation = db.get(Conversation, payload.conversation_id)

        if not conversation or conversation.organization_id != organization_id:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found in this organization",
            )

    ticket = SupportTicket(
        organization_id=organization_id,
        **payload.model_dump(),
    )

    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    return ticket


@router.get("/", response_model=list[TicketResponse])
def list_tickets(
    organization_id: UUID,
    db: Session = Depends(get_db),
):
    organization = db.get(Organization, organization_id)

    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")

    statement = (
        select(SupportTicket)
        .where(SupportTicket.organization_id == organization_id)
        .order_by(SupportTicket.created_at.desc())
    )

    return db.scalars(statement).all()


@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(
    organization_id: UUID,
    ticket_id: UUID,
    db: Session = Depends(get_db),
):
    statement = select(SupportTicket).where(
        SupportTicket.id == ticket_id,
        SupportTicket.organization_id == organization_id,
    )

    ticket = db.scalar(statement)

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return ticket


@router.patch("/{ticket_id}", response_model=TicketResponse)
def update_ticket(
    organization_id: UUID,
    ticket_id: UUID,
    payload: TicketUpdate,
    db: Session = Depends(get_db),
):
    statement = select(SupportTicket).where(
        SupportTicket.id == ticket_id,
        SupportTicket.organization_id == organization_id,
    )

    ticket = db.scalar(statement)

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    updates = payload.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one field to update",
        )

    if any(value is None for value in updates.values()):
        raise HTTPException(
            status_code=422,
            detail="Status and priority cannot be null",
        )

    for field, value in updates.items():
        setattr(ticket, field, value)

    db.commit()
    db.refresh(ticket)

    return ticket
