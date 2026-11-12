from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=150)
    organization_slug: str = Field(
        min_length=2,
        max_length=150,
        pattern=r"^[a-z0-9-]+$",
    )
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: UUID
    organization_id: UUID
    email: str
    role: str
    is_active: bool


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
