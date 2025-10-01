import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.core.auth import get_current_user
from src.backend.core.database import get_db
from src.backend.models.user import User
from src.backend.schemas import gpu as gpu_schema
from src.backend.worker import provision_gpu
from src.backend.crud.organization import organization as organization_crud
from src.backend.crud import gpu as gpu_crud
from src.backend.models.gpu import GpuStatus

router = APIRouter()

@router.post(
    "/allocate",
    response_model=gpu_schema.GPUAllocationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Asynchronously requests a new GPU.",
)
async def allocate_gpu(
    *,
    db: AsyncSession = Depends(get_db),
    allocation_request: gpu_schema.GPUAllocationRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Asynchronously requests a new GPU.
    """
    organization = await organization_crud.get(db, id=current_user.organization_id)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )

    active_gpu_count = await organization_crud.get_active_gpu_count(db, organization_id=organization.id)
    if active_gpu_count >= organization.max_active_gpus:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="GPU quota reached. Please deallocate an existing GPU before requesting a new one.",
        )

    task_payload = allocation_request.dict()
    task_payload["user_id"] = str(current_user.id)
    task_payload["organization_id"] = str(current_user.organization_id)
    task = provision_gpu.delay(task_payload)
    
    return {"task_id": str(task.id), "message": "GPU allocation request has been accepted."}


@router.get(
    "/gpus",
    response_model=List[gpu_schema.GPU],
    summary="List GPUs for the organization.",
)
async def list_gpus(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status: Optional[GpuStatus] = None,
):
    """
    List all GPUs for the user's organization.
    """
    gpus = await gpu_crud.gpu.get_multi_by_owner(
        db, organization_id=current_user.organization_id, status=status
    )
    return gpus


@router.get(
    "/gpu/{gpu_id}",
    response_model=gpu_schema.GPU,
    summary="Get a specific GPU by ID.",
)
async def get_gpu(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    gpu_id: uuid.UUID,
):
    """
    Get a specific GPU by ID.
    """
    gpu = await gpu_crud.gpu.get(db, id=gpu_id)
    if not gpu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GPU not found.",
        )
    if gpu.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )
    return gpu
