import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from src.backend.models.gpu import GpuStatus, GpuHealthState


class GPUBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class GPUAllocationRequest(BaseModel):
    """
    Schema for a new GPU allocation request.
    """
    gpu_model: str = Field(..., examples=["NVIDIA A100", "NVIDIA H100"], description="The model of the GPU requested.")


class GPUAllocationResponse(BaseModel):
    """
    Schema for the response to a GPU allocation request.
    """
    task_id: str
    message: str


class GPUCreate(GPUBase):
    pass


class GPUUpdate(BaseModel):
    pass


class GPU(GPUBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    user_id: uuid.UUID
    instance_id: Optional[str]
    instance_public_ip: Optional[str]
    status: GpuStatus
    health_state: GpuHealthState
    lease_expires_at: datetime
    created_at: datetime
    updated_at: datetime