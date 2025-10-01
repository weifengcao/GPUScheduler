from pydantic import BaseModel


class APIKeyBase(BaseModel):
    pass


class APIKeyCreate(APIKeyBase):
    pass


class APIKeyUpdate(APIKeyBase):
    pass
