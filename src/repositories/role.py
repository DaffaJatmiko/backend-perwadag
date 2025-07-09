"""Role repository for RBAC management."""

from typing import List, Optional, Tuple
from datetime import datetime
from sqlalchemy import select, and_, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.user import Role, UserRole
from src.schemas.user import RoleCreate, RoleUpdate


class RoleRepository:
    """Repository for role data access operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, role_data: RoleCreate) -> Role:
        """Create a new role."""
        role = Role(
            name=role_data.name,
            description=role_data.description,
            is_active=True
        )
        
        self.session.add(role)
        await self.session.commit()
        await self.session.refresh(role)
        return role
    
    async def get_by_id(self, role_id: int) -> Optional[Role]:
        """Get role by ID."""
        query = select(Role).where(
            and_(Role.id == role_id, Role.deleted_at.is_(None))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_name(self, name: str) -> Optional[Role]:
        """Get role by name."""
        query = select(Role).where(
            and_(Role.name == name, Role.deleted_at.is_(None))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all_roles(
        self, 
        page: int = 1, 
        size: int = 50,
        is_active: Optional[bool] = None
    ) -> Tuple[List[Role], int]:
        """Get all roles with pagination."""
        # Build query
        query = select(Role).where(Role.deleted_at.is_(None))
        
        # Apply filters
        if is_active is not None:
            query = query.where(Role.is_active == is_active)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        offset = (page - 1) * size
        query = query.offset(offset).limit(size).order_by(Role.name)
        
        # Execute query
        result = await self.session.execute(query)
        roles = result.scalars().all()
        
        return list(roles), total
    
    async def get_roles_by_names(self, role_names: List[str]) -> List[Role]:
        """Get roles by list of names."""
        query = select(Role).where(
            and_(
                Role.name.in_(role_names),
                Role.deleted_at.is_(None),
                Role.is_active == True
            )
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def update(self, role_id: int, role_data: RoleUpdate) -> Optional[Role]:
        """Update role information."""
        role = await self.get_by_id(role_id)
        if not role:
            return None
        
        # Update fields
        update_data = role_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(role, key, value)
        
        role.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(role)
        return role
    
    async def soft_delete(self, role_id: int) -> Optional[Role]:
        """Soft delete role."""
        role = await self.get_by_id(role_id)
        if not role:
            return None
        
        # Check if role is assigned to any users
        user_count_query = select(func.count(UserRole.id)).where(UserRole.role_id == role_id)
        user_count_result = await self.session.execute(user_count_query)
        user_count = user_count_result.scalar()
        
        if user_count > 0:
            raise ValueError(f"Cannot delete role '{role.name}' as it is assigned to {user_count} users")
        
        role.deleted_at = datetime.utcnow()
        role.is_active = False
        role.updated_at = datetime.utcnow()
        
        await self.session.commit()
        return role
    
    async def role_exists(self, name: str, exclude_role_id: Optional[int] = None) -> bool:
        """Check if role name already exists."""
        query = select(Role.id).where(
            and_(
                Role.name == name,
                Role.deleted_at.is_(None)
            )
        )
        
        if exclude_role_id:
            query = query.where(Role.id != exclude_role_id)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None
    
    async def get_role_with_user_count(self, role_id: int) -> Optional[dict]:
        """Get role with user count."""
        role = await self.get_by_id(role_id)
        if not role:
            return None
        
        # Count users with this role
        user_count_query = (
            select(func.count(UserRole.id))
            .where(UserRole.role_id == role_id)
        )
        user_count_result = await self.session.execute(user_count_query)
        user_count = user_count_result.scalar()
        
        return {
            "role": role,
            "user_count": user_count
        }
    
    async def validate_role_names(self, role_names: List[str]) -> Tuple[List[str], List[str]]:
        """Validate role names and return valid/invalid lists."""
        if not role_names:
            return [], []
        
        # Get existing roles
        existing_roles = await self.get_roles_by_names(role_names)
        existing_names = {role.name for role in existing_roles}
        
        valid_names = [name for name in role_names if name in existing_names]
        invalid_names = [name for name in role_names if name not in existing_names]
        
        return valid_names, invalid_names