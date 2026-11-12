from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.organization import Organization
from app.models.user import User
from app.schemas.organization import OrganizationResponse


router = APIRouter(
    prefix="/organizations",
    tags=["Organizations"],
)


@router.get(
    "/me",
    response_model=OrganizationResponse,
)
def get_my_organization(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    organization = db.get(Organization, current_user.organization_id)

    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    return organization
