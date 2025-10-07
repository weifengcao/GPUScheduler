
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field


from typing import Optional

# Shared properties
class UserBase(BaseModel):
    email: EmailStr = Field(..., examples=["user@example.com"])
    role: str = Field("member", examples=["admin", "member"])
    is_active: bool = True
    organization_id: uuid.UUID


# Properties to receive on item creation
class UserCreate(UserBase):
    password: str


# Properties to receive on item update
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


# Properties to return to client
class User(UserBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
