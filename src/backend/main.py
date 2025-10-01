from fastapi import FastAPI

from src.backend.api.v1.api import api_router

app = FastAPI(
    title="GPUScheduler API",
    description="The control plane for the GPUScheduler service.",
    version="0.1.0",
)

app.include_router(api_router, prefix="/api/gpuscheduler/v1")


@app.get("/", summary="Root Endpoint")
async def root():
    """
    Provides a simple welcome message for the API root.
    """
    return {"message": "Welcome to the GPUScheduler API"}


@app.get("/health", summary="Health Check")
async def health_check():
    """
    A simple health check endpoint that returns the API status.
    """
    return {"status": "ok"}