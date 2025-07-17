"""Simplified User Repository tanpa Role tables."""

from typing import List, Optional, Tuple
from datetime import datetime, date
from sqlalchemy import select, and_, or_, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User, PasswordResetToken
from src.models.enums import UserRole
from src.schemas.user import UserCreate, UserUpdate
from src.schemas.filters import UserFilterParams
from src.auth.jwt import get_password_hash


class UserRepository:
    """Simplified user repository dengan single table."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # ===== USER CRUD OPERATIONS =====
    
    async def create(self, user_data: UserCreate, username: str) -> User:
        """Create user dengan single table approach."""
        # Default password untuk semua user
        default_password = "@Kemendag123"
        hashed_password = get_password_hash(default_password)
        
        # Create user instance
        user = User(
            nama=user_data.nama,
            username=username,
            # tempat_lahir=user_data.tempat_lahir,
            # tanggal_lahir=user_data.tanggal_lahir,
            # pangkat=user_data.pangkat,
            jabatan=user_data.jabatan,
            hashed_password=hashed_password,
            email=user_data.email,
            is_active=user_data.is_active,
            role=user_data.role,  # ENUM field
            inspektorat=user_data.inspektorat  # For perwadag
        )
        
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by UUID."""
        query = select(User).where(
            and_(User.id == user_id, User.deleted_at.is_(None))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username (untuk login)."""
        query = select(User).where(
            and_(User.username == username, User.deleted_at.is_(None))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        query = select(User).where(
            and_(User.email == email.lower(), User.deleted_at.is_(None))
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
        return user
    
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
    
    # ===== USER LISTING WITH SIMPLIFIED FILTERS =====
    
    async def get_all_users_filtered(self, filters: UserFilterParams) -> Tuple[List[User], int]:
        """Get users dengan simplified filter (tanpa join ke role table)."""
        
        # Build base query
        query = select(User).where(User.deleted_at.is_(None))
        
        # Apply search filter
        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.where(
                or_(
                    User.nama.ilike(search_term),
                    User.username.ilike(search_term),
                    User.jabatan.ilike(search_term),
                    User.email.ilike(search_term) if filters.search else False,
                    User.inspektorat.ilike(search_term) if filters.search else False
                )
            )
        
        # Apply specific filters
        if filters.is_active is not None:
            query = query.where(User.is_active == filters.is_active)
        
        if filters.jabatan:
            query = query.where(User.jabatan.ilike(f"%{filters.jabatan}%"))
        
        # Role filter (ENUM field - MUCH SIMPLER!)
        if filters.role:
            query = query.where(User.role == filters.role)
        
        # Inspektorat filter (for perwadag)
        if filters.inspektorat:
            query = query.where(User.inspektorat.ilike(f"%{filters.inspektorat}%"))
        
        # Email filter
        if filters.has_email is not None:
            if filters.has_email:
                query = query.where(and_(User.email.is_not(None), User.email != ""))
            else:
                query = query.where(or_(User.email.is_(None), User.email == ""))
        
        # Age filters
        # if filters.min_age or filters.max_age:
        #     today = date.today()
            
        #     if filters.min_age:
        #         max_birth_date = date(today.year - filters.min_age, today.month, today.day)
        #         query = query.where(User.tanggal_lahir <= max_birth_date)
            
        #     if filters.max_age:
        #         min_birth_date = date(today.year - filters.max_age, today.month, today.day)
        #         query = query.where(User.tanggal_lahir >= min_birth_date)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        offset = (filters.page - 1) * filters.size
        query = query.offset(offset).limit(filters.size).order_by(User.created_at.desc())
        
        # Execute query
        result = await self.session.execute(query)
        users = result.scalars().all()
        
        return list(users), total
    
    async def get_users_by_role(self, role: UserRole) -> List[User]:
        """Get all active users dengan specific role."""
        query = select(User).where(
            and_(
                User.role == role,
                User.deleted_at.is_(None),
                User.is_active == True
            )
        ).order_by(User.nama)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    # ===== USER EXISTENCE CHECKS =====
    
    async def username_exists(self, username: str, exclude_user_id: Optional[str] = None) -> bool:
        """Check if username already exists."""
        query = select(User.id).where(
            and_(
                User.username == username,
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
    
    # ===== PASSWORD RESET TOKEN MANAGEMENT =====
    
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
        return result.rowcount > 0
    
    # ===== STATISTICS =====
    
    async def get_user_statistics(self) -> dict:
        """Get comprehensive user statistics."""
        # Total active users
        total_active_query = select(func.count(User.id)).where(
            and_(User.deleted_at.is_(None), User.is_active == True)
        )
        total_active_result = await self.session.execute(total_active_query)
        total_active = total_active_result.scalar() or 0
        
        # Users with email
        users_with_email_query = select(func.count(User.id)).where(
            and_(
                User.deleted_at.is_(None),
                User.is_active == True,
                User.email.is_not(None),
                User.email != ""
            )
        )
        users_with_email_result = await self.session.execute(users_with_email_query)
        users_with_email = users_with_email_result.scalar() or 0
        
        # Users by role (MUCH SIMPLER - no joins!)
        users_by_role_query = (
            select(User.role, func.count(User.id).label('user_count'))
            .where(and_(User.deleted_at.is_(None), User.is_active == True))
            .group_by(User.role)
            .order_by(func.count(User.id).desc())
        )
        users_by_role_result = await self.session.execute(users_by_role_query)
        users_by_role = [
            {"role": row.role.value, "count": row.user_count} 
            for row in users_by_role_result.all()
        ]
        
        # Email completion rate
        email_completion_rate = (users_with_email / total_active * 100) if total_active > 0 else 0
        
        return {
            "total_active_users": total_active,
            "total_users": total_active,
            "users_with_email": users_with_email,
            "users_without_email": total_active - users_with_email,
            "email_completion_rate": round(email_completion_rate, 2),
            "users_by_role": users_by_role
        }

    async def search_perwadag_users_paginated(
        self, 
        search: str = None,
        inspektorat: str = None,
        is_active: bool = True,
        page: int = 1,
        size: int = 50  # Default size untuk search
    ) -> Tuple[List[User], int]:
        """Search perwadag users dengan pagination."""
        
        # Base query hanya untuk perwadag
        query = select(User).where(
            and_(
                User.role == UserRole.PERWADAG,
                User.deleted_at.is_(None)
            )
        )
        
        # Filter by active status
        if is_active is not None:
            query = query.where(User.is_active == is_active)
        
        # Search filter (nama dan inspektorat)
        if search:
            search_term = f"%{search.strip()}%"
            query = query.where(
                or_(
                    User.nama.ilike(search_term),
                    User.inspektorat.ilike(search_term)
                )
            )
        
        # Inspektorat filter
        if inspektorat:
            query = query.where(User.inspektorat.ilike(f"%{inspektorat.strip()}%"))
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        offset = (page - 1) * size
        query = query.offset(offset).limit(size).order_by(User.nama)
        
        # Execute query
        result = await self.session.execute(query)
        users = list(result.scalars().all())
        
        return users, total