from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


TicketStatus = Literal[
    "open",
    "in_progress",
    "resolved",
    "closed",
]

TicketPriority = Literal[
    "low",
    "medium",
    "high",
    "urgent",
]


class TicketCreate(BaseModel):
    conversation_id: UUID | None = None
    customer_email: EmailStr
    subject: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=5)
    priority: TicketPriority = "medium"


class TicketUpdate(BaseModel):
    status: TicketStatus | None = None
    priority: TicketPriority | None = None


class TicketResponse(BaseModel):
    id: UUID
    organization_id: UUID
    conversation_id: UUID | None
    customer_email: str
    subject: str
    description: str
    status: str
    priority: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)