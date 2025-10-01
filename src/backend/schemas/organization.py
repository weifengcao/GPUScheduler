import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


# Shared properties
class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, examples=["My Awesome Company"])
    max_active_gpus: int = Field(5, gt=0, examples=[10])


# Properties to receive on item creation
class OrganizationCreate(OrganizationBase):
    pass


# Properties to receive on item update
class OrganizationUpdate(OrganizationBase):
    pass


# Properties to return to client
class Organization(OrganizationBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)