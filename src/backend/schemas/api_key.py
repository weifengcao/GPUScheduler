import uuid
from datetime import datetime, timedelta
from pydantic import BaseModel, ConfigDict, Field


class APIKeyBase(BaseModel):
    expires_in_days: int | None = Field(
        30,
        description="The number of days from now that the key should expire. If null, the key never expires.",
        gt=0,
    )


class APIKeyCreate(APIKeyBase):
    pass


class APIKeyUpdate(BaseModel):
    # For now, we don't allow updating API keys.
    # This can be extended later.
    pass


class APIKey(BaseModel):
    id: uuid.UUID
    key_prefix: str
    user_id: uuid.UUID
    organization_id: uuid.UUID
    expires_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class APIKeyWithSecret(APIKey):
    key: str = Field(..., description="The full, unhashed API key. This is only returned on creation.")
