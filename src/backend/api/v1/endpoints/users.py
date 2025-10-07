
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.auth import get_current_user, RoleChecker
from src.backend.core.database import get_db
from src.backend.crud.user import user as user_crud
from src.backend.models.user import User
from src.backend.schemas import user as user_schema

router = APIRouter()

admin_role_checker = RoleChecker(["admin"])


@router.post(
    "/",
    response_model=user_schema.User,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user within an organization",
    dependencies=[Depends(admin_role_checker)],
)
async def create_user(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: user_schema.UserCreate,
    current_user: User = Depends(get_current_user),
):
    """
    Create a new user. Only accessible to users with the 'admin' role.
    """
    existing_user = await user_crud.get_by_email(db, email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email '{user_in.email}' already exists.",
        )

    user_in.organization_id = current_user.organization_id
    user = await user_crud.create(db=db, obj_in=user_in)
    return user


@router.get(
    "/",
    response_model=list[user_schema.User],
    summary="List users in the organization",
    dependencies=[Depends(admin_role_checker)],
)
async def get_users(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve a list of users for the current user's organization.
    Only accessible to users with the 'admin' role.
    """
    users = await user_crud.get_users_by_organization(
        db, organization_id=current_user.organization_id, skip=skip, limit=limit
    )
    return users


@router.put(
    "/{user_id}",
    response_model=user_schema.User,
    summary="Update a user",
    dependencies=[Depends(admin_role_checker)],
)
async def update_user(
    *,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID,
    user_in: user_schema.UserUpdate,
    current_user: User = Depends(get_current_user),
):
    """
    Update a user's details. Only accessible to users with the 'admin' role.
    """
    user = await user_crud.get(db=db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found.",
        )

    if user.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to update this user.",
        )

    user = await user_crud.update(db=db, db_obj=user, obj_in=user_in)
    return user
