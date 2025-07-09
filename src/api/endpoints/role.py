"""Role management endpoints for government project."""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.repositories.role import RoleRepository
from src.services.role import RoleService
from src.schemas.user import (
    RoleCreate, RoleUpdate, RoleResponse, RoleListResponse, MessageResponse
)
from src.auth.permissions import require_roles

router = APIRouter()

# Admin-only access for role management
admin_required = require_roles(["admin"])


async def get_role_service(session: AsyncSession = Depends(get_db)) -> RoleService:
    """Get role service dependency."""
    role_repo = RoleRepository(session)
    return RoleService(role_repo)


@router.get("/", response_model=RoleListResponse, summary="Get all roles")
async def get_all_roles(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size (max 100)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: dict = Depends(admin_required),
    role_service: RoleService = Depends(get_role_service)
):
    """
    Get all roles with pagination.
    
    **Accessible by**: Admin only
    
    **Query Parameters**:
    - **page**: Page number (default: 1)
    - **size**: Items per page (default: 50, max: 100)
    - **is_active**: Filter by active status
    
    Returns paginated list of roles.
    """
    return await role_service.get_all_roles(
        page=page,
        size=size,
        is_active=is_active
    )


@router.post("/", response_model=RoleResponse, summary="Create new role (Admin only)")
async def create_role(
    role_data: RoleCreate,
    current_user: dict = Depends(admin_required),
    role_service: RoleService = Depends(get_role_service)
):
    """
    Create a new role.
    
    **Accessible by**: Admin only
    
    **Required fields**:
    - name (lowercase, underscore allowed)
    
    **Optional fields**:
    - description
    
    **Validation**:
    - Role name must be unique
    - Role name must be lowercase
    """
    return await role_service.create_role(role_data)


@router.get("/{role_id}", response_model=RoleResponse, summary="Get role by ID")
async def get_role(
    role_id: int,
    current_user: dict = Depends(admin_required),
    role_service: RoleService = Depends(get_role_service)
):
    """
    Get role by ID.
    
    **Accessible by**: Admin only
    
    Returns detailed role information.
    """
    return await role_service.get_role_or_404(role_id)


@router.get("/{role_id}/details", summary="Get role with user count")
async def get_role_details(
    role_id: int,
    current_user: dict = Depends(admin_required),
    role_service: RoleService = Depends(get_role_service)
):
    """
    Get role details including user count.
    
    **Accessible by**: Admin only
    
    Returns role information and number of users assigned to this role.
    """
    return await role_service.get_role_with_user_count(role_id)


@router.put("/{role_id}", response_model=RoleResponse, summary="Update role (Admin only)")
async def update_role(
    role_id: int,
    role_data: RoleUpdate,
    current_user: dict = Depends(admin_required),
    role_service: RoleService = Depends(get_role_service)
):
    """
    Update role information.
    
    **Accessible by**: Admin only
    
    **Updatable fields**:
    - description, is_active
    
    **Note**: Role name cannot be changed after creation
    """
    return await role_service.update_role(role_id, role_data)


@router.post("/{role_id}/activate", response_model=RoleResponse, summary="Activate role (Admin only)")
async def activate_role(
    role_id: int,
    current_user: dict = Depends(admin_required),
    role_service: RoleService = Depends(get_role_service)
):
    """
    Activate role.
    
    **Accessible by**: Admin only
    
    Sets role's is_active status to True.
    """
    return await role_service.activate_role(role_id)


@router.post("/{role_id}/deactivate", response_model=RoleResponse, summary="Deactivate role (Admin only)")
async def deactivate_role(
    role_id: int,
    current_user: dict = Depends(admin_required),
    role_service: RoleService = Depends(get_role_service)
):
    """
    Deactivate role.
    
    **Accessible by**: Admin only
    
    Sets role's is_active status to False.
    """
    return await role_service.deactivate_role(role_id)


@router.delete("/{role_id}", response_model=MessageResponse, summary="Delete role (Admin only)")
async def delete_role(
    role_id: int,
    current_user: dict = Depends(admin_required),
    role_service: RoleService = Depends(get_role_service)
):
    """
    Delete role.
    
    **Accessible by**: Admin only
    
    **Protection**: Cannot delete role if it's assigned to any users.
    
    **Note**: This is a soft delete - role data is preserved but marked as deleted.
    """
    return await role_service.delete_role(role_id)


@router.post("/initialize-government-roles", response_model=MessageResponse, summary="Initialize default roles (Admin only)")
async def initialize_government_roles(
    current_user: dict = Depends(admin_required),
    role_service: RoleService = Depends(get_role_service)
):
    """
    Initialize default government roles.
    
    **Accessible by**: Admin only
    
    Creates the following default roles if they don't exist:
    - admin (System Administrator)
    - inspektorat_1 (Inspektorat Wilayah 1)
    - inspektorat_2 (Inspektorat Wilayah 2)
    - inspektorat_3 (Inspektorat Wilayah 3)
    - inspektorat_4 (Inspektorat Wilayah 4)
    - perwadag (Perdagangan)
    - bappeda (Badan Perencanaan Pembangunan Daerah)
    - dinas_kesehatan (Dinas Kesehatan)
    - dinas_pendidikan (Dinas Pendidikan)
    - dinas_sosial (Dinas Sosial)
    
    **Safe to run multiple times** - will skip existing roles.
    """
    return await role_service.initialize_government_roles()