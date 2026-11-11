from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MessageCreate(BaseModel):
    sender_type: Literal["customer", "assistant", "agent"]
    content: str = Field(min_length=1)


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    sender_type: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)