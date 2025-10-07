from src.backend.api.v1.endpoints import organizations, gpus, users, api_keys

api_router = APIRouter()
api_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
api_router.include_router(gpus.router, prefix="/gpus", tags=["gpus"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(api_keys.router, prefix="/api-keys", tags=["api-keys"])