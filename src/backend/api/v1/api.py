from fastapi import APIRouter

from src.backend.api.v1.endpoints import organizations, gpus

api_router = APIRouter()
api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
api_router.include_router(gpus.router, prefix="/gpus", tags=["gpus"])