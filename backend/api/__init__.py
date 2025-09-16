from fastapi import APIRouter
from . import health

# Create main API router
api_router = APIRouter()

# Include all route modules
api_router.include_router(health.router, tags=["health"])
