from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class ConversationCreate(BaseModel):
    customer_email: EmailStr


class ConversationResponse(BaseModel):
    id: UUID
    organization_id: UUID
    customer_email: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)