from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.database import get_db
from src.backend.crud.organization import organization as organization_crud
from src.backend.schemas import organization as organization_schema

router = APIRouter()


@router.post(
    "/",
    response_model=organization_schema.Organization,
    status_code=201,
    summary="Create a new organization",
    description="Creates a new organization and returns its details. Organization names must be unique.",
)
async def create_organization(
    *,
    db: AsyncSession = Depends(get_db),
    organization_in: organization_schema.OrganizationCreate,
):
    """
    Create a new organization, ensuring the name is not already in use.
    """
    existing_organization = await organization_crud.get_by_name(db, name=organization_in.name)
    if existing_organization:
        raise HTTPException(
            status_code=409, detail=f"Organization with name '{organization_in.name}' already exists."
        )
    organization = await organization_crud.create(db=db, obj_in=organization_in)
    return organization
