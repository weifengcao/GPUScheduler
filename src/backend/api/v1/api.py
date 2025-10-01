from fastapi import APIRouter

from src.backend.api.v1.endpoints import organizations

api_router = APIRouter()
api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])