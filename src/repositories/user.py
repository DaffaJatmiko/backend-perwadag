"""User repository simplified - nama as username, email via query params."""

from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, and_, or_, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import math

from src.models.user import User, Role, UserRole, PasswordResetToken
from src.schemas.user import UserCreate, UserUpdate
from src.auth.jwt import get_password_hash


class UserRepository:
    """Repository for user data access operations (simplified)."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # User CRUD operations
    async def create(self, user_data: UserCreate) -> User:
        """Create a new user with nama as username and default password."""
        # Default password for all users
        default_password = "@Kemendag123"
        hashed_password = get_password_hash(default_password)
        
        # Create user instance
        user = User(
            nama=user_data.nama,
            tempat_lahir=user_data.tempat_lahir,
            tanggal_lahir=user_data.tanggal_lahir,
            pangkat=user_data.pangkat,
            jabatan=user_data.jabatan,
            hashed_password=hashed_password,
            email=user_data.email,  # Optional
            is_active=user_data.is_active
        )
        
        self.session.add(user)
        await self.session.flush()  # Get user ID
        
        # Assign roles
        if user_data.role_names:
            await self._assign_roles_to_user(user.id, user_data.role_names)
        
        await self.session.commit()
        await self.session.refresh(user)
        
        # Load roles
        return await self.get_by_id(user.id)
    
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by UUID with roles."""
        query = (
            select(User)
            .options(selectinload(User.roles).selectinload(UserRole.role))
            .where(and_(User.id == user_id, User.deleted_at.is_(None)))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_nama(self, nama: str) -> Optional[User]:
        """Get user by nama (which is the username) with roles."""
        query = (
            select(User)
            .options(selectinload(User.roles).selectinload(UserRole.role))
            .where(and_(User.nama == nama, User.deleted_at.is_(None)))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email with roles."""
        query = (
            select(User)
            .options(selectinload(User.roles).selectinload(UserRole.role))
            .where(and_(User.email == email.lower(), User.deleted_at.is_(None)))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def update(self, user_id: str, user_data: UserUpdate) -> Optional[User]:
        """Update user information."""
        user = await self.get_by_id(user_id)
        if not user:
            return None
        
        # Update fields
        update_data = user_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if key == "email" and value:
                # Normalize email
                value = value.lower()
            setattr(user, key, value)
        
        user.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(user)
        
        return await self.get_by_id(user_id)
    
    async def update_password(self, user_id: str, new_hashed_password: str) -> bool:
        """Update user password."""
        query = (
            update(User)
            .where(User.id == user_id)
            .values(
                hashed_password=new_hashed_password,
                updated_at=datetime.utcnow()
            )
        )
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount > 0
    
    async def update_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp."""
        query = (
            update(User)
            .where(User.id == user_id)
            .values(last_login=datetime.utcnow())
        )
        result = await self.session.execute(query)
        await self.session.commit()
        return result.rowcount > 0
    
    async def soft_delete(self, user_id: str) -> Optional[User]:
        """Soft delete user."""
        user = await self.get_by_id(user_id)
        if not user:
            return None
        
        user.deleted_at = datetime.utcnow()
        user.is_active = False
        user.updated_at = datetime.utcnow()
        
        await self.session.commit()
        return user
    
    # User listing with pagination and enhanced filtering
    async def get_all_users(
        self, 
        page: int = 1, 
        size: int = 20,
        search: Optional[str] = None,
        role_name: Optional[str] = None,
        pangkat: Optional[str] = None,
        jabatan: Optional[str] = None,
        has_email: Optional[bool] = None,  # New filter for email status
        is_active: Optional[bool] = None
    ) -> Tuple[List[User], int]:
        """Get all users with pagination and enhanced filters."""
        # Build base query
        query = (
            select(User)
            .options(selectinload(User.roles).selectinload(UserRole.role))
            .where(User.deleted_at.is_(None))
        )
        
        # Apply filters
        conditions = []
        
        if search:
            search_term = f"%{search}%"
            conditions.append(
                or_(
                    User.nama.ilike(search_term),
                    User.tempat_lahir.ilike(search_term),
                    User.pangkat.ilike(search_term),
                    User.jabatan.ilike(search_term),
                    User.email.ilike(search_term) if search_term else False
                )
            )
        
        if is_active is not None:
            conditions.append(User.is_active == is_active)
        
        if pangkat:
            conditions.append(User.pangkat.ilike(f"%{pangkat}%"))
        
        if jabatan:
            conditions.append(User.jabatan.ilike(f"%{jabatan}%"))
        
        # Enhanced email filter
        if has_email is not None:
            if has_email:
                # Users with email set
                conditions.append(
                    and_(User.email.is_not(None), User.email != "")
                )
            else:
                # Users without email
                conditions.append(
                    or_(User.email.is_(None), User.email == "")
                )
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Handle role filter (requires join)
        if role_name:
            query = (
                query
                .join(UserRole, User.id == UserRole.user_id)
                .join(Role, UserRole.role_id == Role.id)
                .where(Role.name == role_name)
            )
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        offset = (page - 1) * size
        query = query.offset(offset).limit(size).order_by(User.created_at.desc())
        
        # Execute query
        result = await self.session.execute(query)
        users = result.scalars().all()
        
        return list(users), total
    
    async def get_users_by_role(self, role_name: str) -> List[User]:
        """Get all users with specific role."""
        query = (
            select(User)
            .options(selectinload(User.roles).selectinload(UserRole.role))
            .join(UserRole, User.id == UserRole.user_id)
            .join(Role, UserRole.role_id == Role.id)
            .where(
                and_(
                    Role.name == role_name,
                    User.deleted_at.is_(None),
                    User.is_active == True
                )
            )
            .order_by(User.nama)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    # User existence checks
    async def nama_exists(self, nama: str, exclude_user_id: Optional[str] = None) -> bool:
        """Check if nama already exists (since nama = username)."""
        query = select(User.id).where(
            and_(
                User.nama == nama,
                User.deleted_at.is_(None)
            )
        )
        
        if exclude_user_id:
            query = query.where(User.id != exclude_user_id)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None
    
    async def email_exists(self, email: str, exclude_user_id: Optional[str] = None) -> bool:
        """Check if email already exists."""
        if not email:
            return False
            
        query = select(User.id).where(
            and_(
                User.email == email.lower(),
                User.deleted_at.is_(None)
            )
        )
        
        if exclude_user_id:
            query = query.where(User.id != exclude_user_id)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None
    
    # Role management
    async def _assign_roles_to_user(self, user_id: str, role_names: List[str]) -> None:
        """Assign roles to user."""
        # Get role IDs
        query = select(Role.id, Role.name).where(Role.name.in_(role_names))
        result = await self.session.execute(query)
        roles = result.all()
        
        # Create user-role associations
        for role_id, role_name in roles:
            user_role = UserRole(
                user_id=user_id,
                role_id=role_id,
                assigned_at=datetime.utcnow()
            )
            self.session.add(user_role)
    
    async def update_user_roles(self, user_id: str, role_names: List[str]) -> bool:
        """Update user roles (replace existing)."""
        # Remove existing roles
        delete_query = delete(UserRole).where(UserRole.user_id == user_id)
        await self.session.execute(delete_query)
        
        # Assign new roles
        await self._assign_roles_to_user(user_id, role_names)
        await self.session.commit()
        return True
    
    async def get_user_roles(self, user_id: str) -> List[Role]:
        """Get user's roles."""
        query = (
            select(Role)
            .join(UserRole, Role.id == UserRole.role_id)
            .where(UserRole.user_id == user_id)
            .order_by(Role.name)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    # Password reset token management
    async def create_password_reset_token(
        self, 
        user_id: str, 
        token: str, 
        expires_at: datetime
    ) -> PasswordResetToken:
        """Create password reset token."""
        # Invalidate existing tokens for this user
        update_query = (
            update(PasswordResetToken)
            .where(and_(PasswordResetToken.user_id == user_id, PasswordResetToken.used == False))
            .values(used=True, used_at=datetime.utcnow())
        )
        await self.session.execute(update_query)
        
        # Create new token
        reset_token = PasswordResetToken(
            user_id=user_id,
            token=token,
            expires_at=expires_at
        )
        self.session.add(reset_token)
        await self.session.commit()
        await self.session.refresh(reset_token)
        return reset_token
    
    async def get_password_reset_token(self, token: str) -> Optional[PasswordResetToken]:
        """Get password reset token."""
        query = select(PasswordResetToken).where(PasswordResetToken.token == token)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def use_password_reset_token(self, token: str) -> bool:
        """Mark password reset token as used."""
        query = (
            update(PasswordResetToken)
            .where(PasswordResetToken.token == token)
            .values(used=True, used_at=datetime.utcnow())
        )
        result = await self.session.execute(query)
        await self.session.commit()