from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.organization import Organization
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    UserResponse,
)


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db),
):
    email = str(payload.email).lower()

    organization = Organization(
        name=payload.organization_name,
        slug=payload.organization_slug,
    )

    try:
        db.add(organization)
        db.flush()

        user = User(
            organization_id=organization.id,
            email=email,
            password_hash=hash_password(payload.password),
            role="admin",
            is_active=True,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account or organization with these details already exists",
        )

    access_token = create_access_token(str(user.id))

    return AuthResponse(
        access_token=access_token,
        user=UserResponse(
            id=user.id,
            organization_id=user.organization_id,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
        ),
    )


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
):
    email = str(payload.email).lower()

    statement = select(User).where(User.email == email)
    user = db.scalar(statement)

    if (
        user is None
        or not user.is_active
        or not verify_password(payload.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(str(user.id))

    return AuthResponse(
        access_token=access_token,
        user=UserResponse(
            id=user.id,
            organization_id=user.organization_id,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
        ),
    )
