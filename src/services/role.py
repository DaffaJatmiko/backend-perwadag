"""Clean role service - simple dan to the point."""

from typing import Optional
from fastapi import HTTPException, status

from src.repositories.role import RoleRepository
from src.schemas.user import (
    RoleCreate, RoleUpdate, RoleResponse, RoleListResponse, MessageResponse
)
from src.schemas.filters import RoleFilterParams


class RoleService:
    """Simple role service tanpa bloat."""
    
    def __init__(self, role_repo: RoleRepository):
        self.role_repo = role_repo
    
    async def create_role(self, role_data: RoleCreate) -> RoleResponse:
        """Create role dengan validation."""
        if await self.role_repo.role_exists(role_data.name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role '{role_data.name}' already exists"
            )
        
        role = await self.role_repo.create(role_data)
        return RoleResponse.model_validate(role)
    
    async def get_role_or_404(self, role_id: str) -> RoleResponse:
        """Get role by ID or raise 404."""
        role = await self.role_repo.get_by_id(role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        return RoleResponse.model_validate(role)
    
    async def update_role(self, role_id: str, role_data: RoleUpdate) -> RoleResponse:
        """Update role."""
        updated_role = await self.role_repo.update(role_id, role_data)
        if not updated_role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        return RoleResponse.model_validate(updated_role)
    
    async def delete_role(self, role_id: str) -> MessageResponse:
        """Delete role dengan validation."""
        try:
            role = await self.role_repo.soft_delete(role_id)
            if not role:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Role not found"
                )
            return MessageResponse(message=f"Role '{role.name}' deleted successfully")
            
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    
    async def get_all_roles(self, filters: RoleFilterParams) -> RoleListResponse:
        """Get all roles dengan clean filtering."""
        roles, total = await self.role_repo.get_all_roles_filtered(filters)
        
        return RoleListResponse(
            roles=[RoleResponse.model_validate(role) for role in roles],
            total=total
        )