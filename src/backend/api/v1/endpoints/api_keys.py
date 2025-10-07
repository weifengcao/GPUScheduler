
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.auth import get_current_user
from src.backend.core.database import get_db
from src.backend.crud.api_key import api_key as api_key_crud
from src.backend.models.user import User
from src.backend.schemas import api_key as api_key_schema

router = APIRouter()


@router.post(
    "/",
    response_model=api_key_schema.APIKeyWithSecret,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API key",
)
async def create_api_key(
    *,
    db: AsyncSession = Depends(get_db),
    api_key_in: api_key_schema.APIKeyCreate,
    current_user: User = Depends(get_current_user),
):
    """
    Create a new API key for the current user.
    The key secret is only returned on creation and is not stored in plaintext.
    """
    db_api_key, secret = await api_key_crud.create_with_owner(
        db=db, obj_in=api_key_in, owner=current_user
    )
    return {**db_api_key.__dict__, "key": secret}


@router.get("/", response_model=list[api_key_schema.APIKey], summary="List API keys")
async def get_api_keys(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve a list of API keys for the current user.
    """
    api_keys = await api_key_crud.get_multi_by_user(
        db, user_id=current_user.id, skip=skip, limit=limit
    )
    return api_keys
