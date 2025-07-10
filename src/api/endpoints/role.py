"""Clean role endpoints - simple dan focused."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.repositories.role import RoleRepository
from src.services.role import RoleService
from src.schemas.user import (
    RoleCreate, RoleUpdate, RoleResponse, RoleListResponse, MessageResponse
)
from src.schemas.filters import RoleFilterParams
from src.auth.permissions import admin_required

router = APIRouter()


async def get_role_service(session: AsyncSession = Depends(get_db)) -> RoleService:
    """Get role service dependency."""
    role_repo = RoleRepository(session)
    return RoleService(role_repo)


@router.get("/", response_model=RoleListResponse)
async def get_all_roles(
    filters: RoleFilterParams = Depends(),
    current_user: dict = Depends(admin_required),
    role_service: RoleService = Depends(get_role_service)
):
    """Get all roles dengan filtering."""
    return await role_service.get_all_roles(filters)


@router.post("/", response_model=RoleResponse, status_code=201)
async def create_role(
    role_data: RoleCreate,
    current_user: dict = Depends(admin_required),
    role_service: RoleService = Depends(get_role_service)
):
    """Create new role."""
    return await role_service.create_role(role_data)


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: str,
    current_user: dict = Depends(admin_required),
    role_service: RoleService = Depends(get_role_service)
):
    """Get role by ID."""
    return await role_service.get_role_or_404(role_id)


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: str,
    role_data: RoleUpdate,
    current_user: dict = Depends(admin_required),
    role_service: RoleService = Depends(get_role_service)
):
    """Update role."""
    return await role_service.update_role(role_id, role_data)


@router.delete("/{role_id}", response_model=MessageResponse)
async def delete_role(
    role_id: str,
    current_user: dict = Depends(admin_required),
    role_service: RoleService = Depends(get_role_service)
):
    """Delete role."""
    return await role_service.delete_role(role_id)