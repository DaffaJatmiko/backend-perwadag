"""Role service for RBAC management."""

from typing import List, Optional
from fastapi import HTTPException, status
import math

from src.repositories.role import RoleRepository
from src.schemas.user import (
    RoleCreate, RoleUpdate, RoleResponse, RoleListResponse, MessageResponse
)
from src.models.user import Role


class RoleService:
    """Service for role management operations."""
    
    def __init__(self, role_repo: RoleRepository):
        self.role_repo = role_repo
    
    async def create_role(self, role_data: RoleCreate) -> RoleResponse:
        """Create a new role with validation."""
        # Check if role name already exists
        if await self.role_repo.role_exists(role_data.name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role '{role_data.name}' already exists"
            )
        
        # Create role
        role = await self.role_repo.create(role_data)
        
        return RoleResponse.model_validate(role)
    
    async def get_role(self, role_id: int) -> Optional[RoleResponse]:
        """Get role by ID."""
        role = await self.role_repo.get_by_id(role_id)
        if not role:
            return None
        
        return RoleResponse.model_validate(role)
    
    async def get_role_or_404(self, role_id: int) -> RoleResponse:
        """Get role by ID or raise 404."""
        role = await self.get_role(role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        return role
    
    async def get_role_by_name(self, name: str) -> Optional[RoleResponse]:
        """Get role by name."""
        role = await self.role_repo.get_by_name(name)
        if not role:
            return None
        
        return RoleResponse.model_validate(role)
    
    async def update_role(self, role_id: int, role_data: RoleUpdate) -> RoleResponse:
        """Update role information."""
        # Check if role exists
        existing_role = await self.role_repo.get_by_id(role_id)
        if not existing_role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        
        # Update role
        updated_role = await self.role_repo.update(role_id, role_data)
        
        return RoleResponse.model_validate(updated_role)
    
    async def delete_role(self, role_id: int) -> MessageResponse:
        """Delete role with validation."""
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
    
    async def get_all_roles(
        self,
        page: int = 1,
        size: int = 50,
        is_active: Optional[bool] = None
    ) -> RoleListResponse:
        """Get all roles with pagination."""
        # Validate pagination parameters
        if page < 1:
            page = 1
        if size < 1:
            size = 50
        if size > 100:  # Prevent too large page sizes
            size = 100
        
        # Get roles with pagination
        roles, total = await self.role_repo.get_all_roles(
            page=page,
            size=size,
            is_active=is_active
        )
        
        # Build response
        role_responses = [RoleResponse.model_validate(role) for role in roles]
        
        return RoleListResponse(
            roles=role_responses,
            total=total
        )
    
    async def activate_role(self, role_id: int) -> RoleResponse:
        """Activate role."""
        role_data = RoleUpdate(is_active=True)
        return await self.update_role(role_id, role_data)
    
    async def deactivate_role(self, role_id: int) -> RoleResponse:
        """Deactivate role."""
        role_data = RoleUpdate(is_active=False)
        return await self.update_role(role_id, role_data)
    
    async def get_role_with_user_count(self, role_id: int) -> dict:
        """Get role with user count."""
        role_info = await self.role_repo.get_role_with_user_count(role_id)
        if not role_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        
        return {
            "role": RoleResponse.model_validate(role_info["role"]),
            "user_count": role_info["user_count"]
        }
    
    async def initialize_government_roles(self) -> MessageResponse:
        """Initialize default government roles."""
        default_roles = [
            {"name": "admin", "description": "System Administrator"},
            {"name": "inspektorat_1", "description": "Inspektorat Wilayah 1"},
            {"name": "inspektorat_2", "description": "Inspektorat Wilayah 2"},
            {"name": "inspektorat_3", "description": "Inspektorat Wilayah 3"},
            {"name": "inspektorat_4", "description": "Inspektorat Wilayah 4"},
            {"name": "perwadag", "description": "Perdagangan"},
            {"name": "bappeda", "description": "Badan Perencanaan Pembangunan Daerah"},
            {"name": "dinas_kesehatan", "description": "Dinas Kesehatan"},
            {"name": "dinas_pendidikan", "description": "Dinas Pendidikan"},
            {"name": "dinas_sosial", "description": "Dinas Sosial"},
        ]
        
        created_roles = []
        skipped_roles = []
        
        for role_data in default_roles:
            # Check if role already exists
            existing_role = await self.role_repo.get_by_name(role_data["name"])
            if existing_role:
                skipped_roles.append(role_data["name"])
                continue
            
            # Create role
            role_create = RoleCreate(
                name=role_data["name"],
                description=role_data["description"]
            )
            
            try:
                await self.role_repo.create(role_create)
                created_roles.append(role_data["name"])
            except Exception as e:
                print(f"Failed to create role {role_data['name']}: {e}")
                continue
        
        message_parts = []
        if created_roles:
            message_parts.append(f"Created roles: {', '.join(created_roles)}")
        if skipped_roles:
            message_parts.append(f"Skipped existing roles: {', '.join(skipped_roles)}")
        
        message = "; ".join(message_parts) if message_parts else "No roles were created"
        
        return MessageResponse(message=message)