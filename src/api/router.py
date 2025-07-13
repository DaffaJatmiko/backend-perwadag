"""API router configuration for government project."""

from fastapi import APIRouter

from src.api.endpoints import auth, users

# Create main API router
api_router = APIRouter()

# Include endpoint routers with proper tags and descriptions
api_router.include_router(
    auth.router, 
    prefix="/auth", 
    tags=["Authentication"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        422: {"description": "Validation Error"},
    }
)

api_router.include_router(
    users.router, 
    prefix="/users", 
    tags=["User Management"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "User not found"},
        422: {"description": "Validation Error"},
    }
)

