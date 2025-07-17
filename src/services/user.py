"""Simplified User service tanpa Role tables."""

from typing import Optional, List
from fastapi import HTTPException, status

from src.repositories.user import UserRepository
from src.schemas.user import (
    UserCreate, UserUpdate, UserResponse, UserListResponse, 
    UserChangePassword, MessageResponse, PerwadagListResponse, PerwadagSummary
)
from src.schemas.filters import UserFilterParams, UsernameGenerationPreview, UsernameGenerationResponse
from src.auth.jwt import get_password_hash, verify_password
from src.models.user import User
from src.models.enums import UserRole
from src.utils.username_generator import generate_username_from_name_and_inspektorat, generate_available_username

class UserService:
    """Simplified user service dengan single table approach."""
    
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo
        # No more role_repo needed!
    
    async def create_user(self, user_data: UserCreate) -> UserResponse:
        """Create user dengan simplified validation."""
        # 1. Validate inspektorat for admin/inspektorat roles
        if user_data.role in [UserRole.ADMIN, UserRole.INSPEKTORAT]:
            if not user_data.inspektorat:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Inspektorat is required for admin and inspektorat roles"
                )
        
        # 2. Validate email uniqueness
        if user_data.email and await self.user_repo.email_exists(user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # 3. Generate username based on role
        username = self._generate_username_by_role(user_data.nama, user_data.role, user_data.inspektorat)
        
        # 4. Check username availability and resolve conflicts
        if await self.user_repo.username_exists(username):
            username = await self._generate_available_username(
                user_data.nama, user_data.role, user_data.inspektorat
            )
        
        # 5. Create user in database
        user = await self.user_repo.create(user_data, username)
        
        # 6. Convert Model → Schema Response
        return UserResponse.from_user_model(user)
    
    async def get_user_or_404(self, user_id: str) -> UserResponse:
        """Get user by ID or raise 404."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return UserResponse.from_user_model(user)
    
    async def update_user(self, user_id: str, user_data: UserUpdate) -> UserResponse:
        """Update user information."""
        # 1. Check if user exists
        existing_user = await self.user_repo.get_by_id(user_id)
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # 2. Validate email uniqueness if being updated
        if user_data.email and await self.user_repo.email_exists(user_data.email, exclude_user_id=user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # 3. If role changed to/from perwadag, validate inspektorat
        if user_data.role:
            if user_data.role == UserRole.PERWADAG and not user_data.inspektorat:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Inspektorat is required for role 'perwadag'"
                )
            elif user_data.role != UserRole.PERWADAG and user_data.inspektorat:
                # Auto-clear inspektorat for non-perwadag roles
                user_data.inspektorat = None
        
        # 4. Update user in database
        updated_user = await self.user_repo.update(user_id, user_data)
        
        # 5. Convert Model → Schema Response
        return UserResponse.from_user_model(updated_user)
    
    async def change_password(self, user_id: str, password_data: UserChangePassword) -> MessageResponse:
        """Change user password."""
        # 1. Get user
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # 2. Verify current password
        if not verify_password(password_data.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # 3. Check if new password is different
        if verify_password(password_data.new_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from current password"
            )
        
        # 4. Update password
        new_hashed_password = get_password_hash(password_data.new_password)
        success = await self.user_repo.update_password(user_id, new_hashed_password)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update password"
            )
        
        return MessageResponse(message="Password changed successfully")
    
    async def reset_user_password(self, user_id: str) -> MessageResponse:
        """Reset user password to default (admin only)."""
        # 1. Get user
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # 2. Reset to default password
        default_password = "@Kemendag123"
        new_hashed_password = get_password_hash(default_password)
        success = await self.user_repo.update_password(user_id, new_hashed_password)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reset password"
            )
        
        return MessageResponse(message=f"Password reset to default for user {user.nama}")
    
    async def delete_user(self, user_id: str) -> MessageResponse:
        """Soft delete user."""
        # 1. Get user
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # 2. Check if user is admin (prevent deleting last admin)
        if user.role == UserRole.ADMIN:
            admin_users = await self.user_repo.get_users_by_role(UserRole.ADMIN)
            if len(admin_users) <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete the last admin user"
                )
        
        # 3. Soft delete
        await self.user_repo.soft_delete(user_id)
        
        return MessageResponse(message=f"User {user.nama} deleted successfully")
    
    async def get_all_users_with_filters(self, filters: UserFilterParams) -> UserListResponse:
        """Get users dengan simplified filters."""
        # 1. Get users from repository
        users, total = await self.user_repo.get_all_users_filtered(filters)
                
        # 3. Convert semua models ke responses
        user_responses = [UserResponse.from_user_model(user) for user in users]
        
        pages = (total + filters.size - 1) // filters.size if total > 0 else 0

        return UserListResponse(
            items=user_responses,  # ✅ users → items
            total=total,
            page=filters.page,
            size=filters.size,
            pages=pages
        )
    
    async def get_users_by_role(self, role: UserRole) -> List[UserResponse]:
        """Get users by role (simplified)."""
        users = await self.user_repo.get_users_by_role(role)
        return [UserResponse.from_user_model(user) for user in users]
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user untuk login."""
        # 1. Get user by username
        user = await self.user_repo.get_by_username(username)
        if not user:
            return None
        
        # 2. Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated"
            )
        
        # 3. Verify password
        if not verify_password(password, user.hashed_password):
            return None
        
        # 4. Update last login
        await self.user_repo.update_last_login(user.id)
        
        return user
    
    async def get_user_statistics(self) -> dict:
        """Get user statistics."""
        return await self.user_repo.get_user_statistics()
    
    async def preview_username_generation(self, preview_data: UsernameGenerationPreview) -> UsernameGenerationResponse:
        """Preview username generation."""
        # REMOVE tanggal_lahir parsing
        
        # Generate username
        if preview_data.role == UserRole.PERWADAG:
            username = self._generate_perwadag_username(preview_data.nama)
        else:
            if not preview_data.inspektorat:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Inspektorat is required for admin and inspektorat roles"
                )
            username = generate_username_from_name_and_inspektorat(
                preview_data.nama, preview_data.inspektorat
            )
        
        # Check availability
        is_available = not await self.user_repo.username_exists(username)
        
        # Generate alternatives if needed
        alternatives = []
        if not is_available:
            if preview_data.role != UserRole.PERWADAG:
                # Try conflict resolution
                conflict_username = generate_username_with_conflict_resolution(
                    preview_data.nama, preview_data.inspektorat
                )
                alternatives.append(conflict_username)
            
            # Add numbered alternatives
            alternatives.extend(
                await self._generate_username_alternatives_simple(username, count=4)
            )
        
        return UsernameGenerationResponse(
            original_nama=preview_data.nama,
            inspektorat=preview_data.inspektorat,
            role=preview_data.role,
            generated_username=username,
            is_available=is_available,
            suggested_alternatives=alternatives
        )
    
    async def activate_user(self, user_id: str) -> UserResponse:
        """Activate user."""
        user_data = UserUpdate(is_active=True)
        return await self.update_user(user_id, user_data)
    
    async def deactivate_user(self, user_id: str) -> UserResponse:
        """Deactivate user."""
        # Check if it's the last admin
        user = await self.user_repo.get_by_id(user_id)
        if user and user.role == UserRole.ADMIN:
            admin_users = await self.user_repo.get_users_by_role(UserRole.ADMIN)
            active_admins = [u for u in admin_users if u.is_active and u.id != user_id]
            if len(active_admins) == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot deactivate the last active admin user"
                )
        
        user_data = UserUpdate(is_active=False)
        return await self.update_user(user_id, user_data)
    
    # ===== PRIVATE HELPER METHODS =====
    
    def _generate_username_by_role(self, nama: str, role: UserRole, inspektorat: str = None) -> str:
        """Generate username based on role."""
        if role == UserRole.PERWADAG:
            return self._generate_perwadag_username(nama)
        else:  # ADMIN or INSPEKTORAT
            if not inspektorat:
                raise ValueError("Inspektorat required for admin/inspektorat roles")
            return generate_username_from_name_and_inspektorat(nama, inspektorat)
    
    def _generate_perwadag_username(self, nama: str) -> str:
        """Generate username untuk perwadag dari nama."""
        # Normalize nama perwadag
        # "ITPC Lagos – Nigeria" -> "itpc_lagos"
        # "Atdag Moscow – Rusia" -> "atdag_moscow"
        
        import re
        import unicodedata
        
        # Remove unicode and normalize
        nama = unicodedata.normalize('NFD', nama)
        nama = ''.join(c for c in nama if unicodedata.category(c) != 'Mn')
        
        # Convert to lowercase
        nama = nama.lower()
        
        # Split by common separators and take first two meaningful parts
        parts = re.split(r'[–—\-\s]+', nama)
        meaningful_parts = [part.strip() for part in parts if part.strip() and len(part.strip()) > 1]
        
        if len(meaningful_parts) >= 2:
            username = f"{meaningful_parts[0]}_{meaningful_parts[1]}"
        else:
            username = meaningful_parts[0] if meaningful_parts else "perwadag"
        
        # Clean username
        username = re.sub(r'[^a-z0-9_]', '', username)
        return username[:50]  # Limit length
    
    async def _generate_available_username(self, nama: str, role: UserRole, inspektorat: str = None) -> str:
        """Generate available username dengan fallback."""
        if role == UserRole.PERWADAG:
            # Use existing perwadag logic
            base_username = self._generate_perwadag_username(nama)
            alternatives = await self._generate_username_alternatives_perwadag(nama, count=10)
        else:
            # Use new inspektorat logic
            if not inspektorat:
                raise ValueError("Inspektorat required for admin/inspektorat roles")
            
            result = await generate_available_username(
                nama, inspektorat, role, self.user_repo.username_exists
            )
            return result["username"]
        
        # Fallback for perwadag
        for username in alternatives:
            if not await self.user_repo.username_exists(username):
                return username
        
        # Ultimate fallback
        import time
        return f"{base_username}{int(time.time()) % 1000}"
    
    async def _generate_username_alternatives(self, nama: str, tanggal_lahir, role: UserRole, count: int = 5) -> List[str]:
        """Generate username alternatives."""
        base_username = self._generate_username_by_role(nama, tanggal_lahir, role)
        alternatives = []
        
        # Add number suffixes
        for i in range(1, count + 1):
            alternatives.append(f"{base_username}{i}")
        
        # Add letter suffixes
        for letter in ['a', 'b', 'c', 'd', 'e']:
            if len(alternatives) < count:
                alternatives.append(f"{base_username}{letter}")
        
        return alternatives[:count]

    async def search_perwadag_users(
        self, 
        search: str = None,
        inspektorat: str = None,
        is_active: bool = True,
        page: int = 1,
        size: int = 50
    ) -> PerwadagListResponse:
        """Search perwadag users dengan response yang konsisten."""
        
        # Get users dari repository dengan pagination
        users, total = await self.user_repo.search_perwadag_users_paginated(
            search, inspektorat, is_active, page, size
        )
        
        # Convert ke PerwadagSummary
        perwadag_list = [PerwadagSummary.from_user_model(user) for user in users]
        
        # Calculate pages
        pages = (total + size - 1) // size if total > 0 else 0
        
        return PerwadagListResponse(
            items=perwadag_list,
            total=total,
            page=page,
            size=size,
            pages=pages
        )

    async def _generate_username_alternatives_simple(self, base_username: str, count: int = 5) -> List[str]:
        """Generate simple numbered alternatives."""
        alternatives = []
        for i in range(1, count + 1):
            alternatives.append(f"{base_username}{i}")
        return alternatives