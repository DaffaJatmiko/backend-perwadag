"""User service with business logic for government project (revised)."""

from typing import Optional, List, Tuple
from datetime import datetime, timedelta
from fastapi import HTTPException, status
import math

from src.repositories.user import UserRepository
from src.repositories.role import RoleRepository
from src.schemas.user import (
    UserCreate, UserUpdate, UserResponse, UserListResponse, UserSummary,
    UserUpdateRole, UserChangePassword, UserSetEmail, MessageResponse,
    UsernameGenerationResponse
)
from src.auth.jwt import get_password_hash, verify_password
from src.models.user import User
from src.utils.username_generator import generate_username_from_name, generate_username_alternatives


class UserService:
    """Service for user business logic with government-specific features."""
    
    def __init__(self, user_repo: UserRepository, role_repo: RoleRepository):
        self.user_repo = user_repo
        self.role_repo = role_repo
    
    async def create_user(self, user_data: UserCreate) -> UserResponse:
        """Create a new user with auto-generated username and default password."""
        # Validate email uniqueness if provided
        if user_data.email and await self.user_repo.email_exists(user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Validate roles exist
        valid_roles, invalid_roles = await self.role_repo.validate_role_names(user_data.role_names)
        if invalid_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid roles: {', '.join(invalid_roles)}"
            )
        
        # Create user (username auto-generated, password = @Kemendag123)
        user = await self.user_repo.create(user_data)
        
        return self._build_user_response(user)
    
    async def preview_username_generation(self, nama: str) -> UsernameGenerationResponse:
        """Preview username generation from nama."""
        base_username = generate_username_from_name(nama)
        is_available = await self.user_repo.check_username_availability(base_username)
        
        suggested_alternatives = []
        if not is_available:
            suggested_alternatives = generate_username_alternatives(base_username, 5)
        
        return UsernameGenerationResponse(
            original_nama=nama,
            generated_username=base_username,
            is_available=is_available,
            suggested_alternatives=suggested_alternatives
        )
    
    async def get_user(self, user_id: str) -> Optional[UserResponse]:
        """Get user by UUID."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return None
        
        return self._build_user_response(user)
    
    async def get_user_or_404(self, user_id: str) -> UserResponse:
        """Get user by UUID or raise 404."""
        user = await self.get_user(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user
    
    async def update_user(self, user_id: str, user_data: UserUpdate) -> UserResponse:
        """Update user information."""
        # Check if user exists
        existing_user = await self.user_repo.get_by_id(user_id)
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Validate email uniqueness if being updated
        if user_data.email and await self.user_repo.email_exists(user_data.email, exclude_user_id=user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Update user
        updated_user = await self.user_repo.update(user_id, user_data)
        
        return self._build_user_response(updated_user)
    
    async def set_user_email(self, user_id: str, email_data: UserSetEmail) -> UserResponse:
        """Set user email (required before password reset)."""
        # Check if user exists
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check email uniqueness
        if await self.user_repo.email_exists(email_data.email, exclude_user_id=user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Set email
        success = await self.user_repo.set_user_email(user_id, email_data.email)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update email"
            )
        
        # Return updated user
        updated_user = await self.user_repo.get_by_id(user_id)
        return self._build_user_response(updated_user)
    
    async def update_user_roles(self, user_id: str, role_data: UserUpdateRole) -> UserResponse:
        """Update user roles."""
        # Check if user exists
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Validate roles exist
        valid_roles, invalid_roles = await self.role_repo.validate_role_names(role_data.role_names)
        if invalid_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid roles: {', '.join(invalid_roles)}"
            )
        
        # Update roles
        await self.user_repo.update_user_roles(user_id, valid_roles)
        
        # Return updated user
        updated_user = await self.user_repo.get_by_id(user_id)
        return self._build_user_response(updated_user)
    
    async def change_password(self, user_id: str, password_data: UserChangePassword) -> MessageResponse:
        """Change user password."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify current password
        if not verify_password(password_data.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Check if new password is different
        if verify_password(password_data.new_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from current password"
            )
        
        # Hash new password
        new_hashed_password = get_password_hash(password_data.new_password)
        
        # Update password
        success = await self.user_repo.update_password(user_id, new_hashed_password)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update password"
            )
        
        return MessageResponse(message="Password changed successfully")
    
    async def reset_user_password(self, user_id: str) -> MessageResponse:
        """Reset user password to default (admin only)."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Reset to default password
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
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if user has admin role (prevent deleting admin)
        user_roles = [role.role.name for role in user.roles]
        if "admin" in user_roles:
            # Count other admin users
            admin_users = await self.user_repo.get_users_by_role("admin")
            if len(admin_users) <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete the last admin user"
                )
        
        await self.user_repo.soft_delete(user_id)
        
        return MessageResponse(message=f"User {user.nama} deleted successfully")
    
    async def activate_user(self, user_id: str) -> UserResponse:
        """Activate user."""
        user_data = UserUpdate(is_active=True)
        return await self.update_user(user_id, user_data)
    
    async def deactivate_user(self, user_id: str) -> UserResponse:
        """Deactivate user."""
        # Check if user has admin role
        user = await self.user_repo.get_by_id(user_id)
        if user:
            user_roles = [role.role.name for role in user.roles]
            if "admin" in user_roles:
                admin_users = await self.user_repo.get_users_by_role("admin")
                active_admins = [u for u in admin_users if u.is_active and u.id != user_id]
                if len(active_admins) == 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Cannot deactivate the last active admin user"
                    )
        
        user_data = UserUpdate(is_active=False)
        return await self.update_user(user_id, user_data)
    
    async def get_all_users(
        self,
        page: int = 1,
        size: int = 20,
        search: Optional[str] = None,
        role_name: Optional[str] = None,
        pangkat: Optional[str] = None,
        jabatan: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> UserListResponse:
        """Get all users with pagination and filters."""
        # Validate pagination parameters
        if page < 1:
            page = 1
        if size < 1:
            size = 20
        if size > 100:  # Prevent too large page sizes
            size = 100
        
        # Get users with filters
        users, total = await self.user_repo.get_all_users(
            page=page,
            size=size,
            search=search,
            role_name=role_name,
            pangkat=pangkat,
            jabatan=jabatan,
            is_active=is_active
        )
        
        # Calculate pagination info
        pages = math.ceil(total / size) if total > 0 else 1
        
        # Build response
        user_responses = [self._build_user_response(user) for user in users]
        
        return UserListResponse(
            users=user_responses,
            total=total,
            page=page,
            size=size,
            pages=pages
        )
    
    async def get_users_by_role(self, role_name: str) -> List[UserSummary]:
        """Get all users with specific role."""
        users = await self.user_repo.get_users_by_role(role_name)
        return [self._build_user_summary(user) for user in users]
    
    async def get_users_without_email(self, page: int = 1, size: int = 20) -> UserListResponse:
        """Get users who haven't set their email."""
        users, total = await self.user_repo.get_users_without_email(page=page, size=size)
        
        # Calculate pagination info
        pages = math.ceil(total / size) if total > 0 else 1
        
        # Build response
        user_responses = [self._build_user_response(user) for user in users]
        
        return UserListResponse(
            users=user_responses,
            total=total,
            page=page,
            size=size,
            pages=pages
        )
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password."""
        user = await self.user_repo.get_by_username(username)
        if not user:
            return None
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated"
            )
        
        if not verify_password(password, user.hashed_password):
            return None
        
        # Update last login
        await self.user_repo.update_last_login(user.id)
        
        return user
    
    async def get_user_statistics(self) -> dict:
        """Get user statistics."""
        return await self.user_repo.get_user_statistics()
    
    def _build_user_response(self, user: User) -> UserResponse:
        """Build UserResponse from User model."""
        return UserResponse(
            id=user.id,
            nama=user.nama,
            tempat_lahir=user.tempat_lahir,
            tanggal_lahir=user.tanggal_lahir,
            pangkat=user.pangkat,
            jabatan=user.jabatan,
            username=user.username,
            email=user.email,
            display_name=user.display_name,
            age=user.age,
            has_email=user.has_email(),
            is_active=user.is_active,
            last_login=user.last_login,
            roles=[
                {
                    "id": role.role.id,
                    "name": role.role.name,
                    "description": role.role.description,
                    "is_active": role.role.is_active
                }
                for role in user.roles
            ],
            created_at=user.created_at,
            updated_at=user.updated_at
        )
    
    def _build_user_summary(self, user: User) -> UserSummary:
        """Build UserSummary from User model."""
        return UserSummary(
            id=user.id,
            nama=user.nama,
            username=user.username,
            pangkat=user.pangkat,
            jabatan=user.jabatan,
            has_email=user.has_email(),
            is_active=user.is_active,
            roles=[role.role.name for role in user.roles]
        )