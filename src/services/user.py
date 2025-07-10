"""Clean User service - final version yang simple dan jelas."""

from typing import Optional
from fastapi import HTTPException, status

from src.repositories.user import UserRepository
from src.repositories.role import RoleRepository
from src.schemas.user import (
    UserCreate, UserUpdate, UserResponse, UserListResponse, 
    UserUpdateRole, UserChangePassword, MessageResponse
)
from src.schemas.filters import UserFilterParams
from src.auth.jwt import get_password_hash, verify_password
from src.models.user import User
from src.utils.username_generator import generate_username_from_name_and_date


class UserService:
    """Clean user service dengan business logic yang focused."""
    
    def __init__(self, user_repo: UserRepository, role_repo: RoleRepository):
        self.user_repo = user_repo
        self.role_repo = role_repo
    
    async def create_user(self, user_data: UserCreate) -> UserResponse:
        """Create user dengan auto-generated username."""
        # 1. Validate email uniqueness
        if user_data.email and await self.user_repo.email_exists(user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # 2. Generate username
        username = generate_username_from_name_and_date(user_data.nama, user_data.tanggal_lahir)
        
        # 3. Check username availability
        if await self.user_repo.username_exists(username):
            username = await self._generate_available_username(user_data.nama, user_data.tanggal_lahir)
        
        # 4. Validate roles exist
        valid_roles, invalid_roles = await self.role_repo.validate_role_names(user_data.role_names)
        if invalid_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid roles: {', '.join(invalid_roles)}"
            )
        
        # 5. Create user in database
        user = await self.user_repo.create(user_data, username)
        
        # 6. Convert Model → Schema Response
        return self._model_to_response(user)
    
    async def get_user_or_404(self, user_id: str) -> UserResponse:
        """Get user by ID or raise 404."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return self._model_to_response(user)
    
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
        
        # 3. Update user in database
        updated_user = await self.user_repo.update(user_id, user_data)
        
        # 4. Convert Model → Schema Response
        return self._model_to_response(updated_user)
    
    async def update_user_roles(self, user_id: str, role_data: UserUpdateRole) -> UserResponse:
        """Update user roles."""
        # 1. Check if user exists
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # 2. Validate roles exist
        valid_roles, invalid_roles = await self.role_repo.validate_role_names(role_data.role_names)
        if invalid_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid roles: {', '.join(invalid_roles)}"
            )
        
        # 3. Update roles in database
        await self.user_repo.update_user_roles(user_id, valid_roles)
        
        # 4. Get updated user and convert to response
        updated_user = await self.user_repo.get_by_id(user_id)
        return self._model_to_response(updated_user)
    
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
        
        # 2. Check if user has admin role (prevent deleting last admin)
        user_roles = [role.role.name for role in user.roles]
        if "admin" in user_roles:
            admin_users = await self.user_repo.get_users_by_role("admin")
            if len(admin_users) <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete the last admin user"
                )
        
        # 3. Soft delete
        await self.user_repo.soft_delete(user_id)
        
        return MessageResponse(message=f"User {user.nama} deleted successfully")
    
    async def get_all_users(self, filters: UserFilterParams) -> UserListResponse:
        """Get users dengan clean filter schema."""
        # 1. Get users from repository dengan filter schema
        users, total = await self.user_repo.get_all_users_filtered(filters)
        
        # 2. Calculate pagination
        pages = (total + filters.size - 1) // filters.size
        
        # 3. Convert semua models ke responses
        user_responses = [self._model_to_response(user) for user in users]
        
        return UserListResponse(
            users=user_responses,
            total=total,
            page=filters.page,
            size=filters.size,
            pages=pages
        )
    
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
    
    # ===== PRIVATE HELPER METHODS =====
    
    async def _generate_available_username(self, nama: str, tanggal_lahir) -> str:
        """Generate available username dengan fallback."""
        from src.utils.username_generator import generate_username_alternatives
        
        base_username = generate_username_from_name_and_date(nama, tanggal_lahir)
        alternatives = generate_username_alternatives(base_username, 10)
        
        for username in alternatives:
            if not await self.user_repo.username_exists(username):
                return username
        
        # Ultimate fallback dengan timestamp
        import time
        return f"{base_username}{int(time.time()) % 1000}"
    
    def _model_to_response(self, user: User) -> UserResponse:
        """
        Convert Database Model ke API Response Schema.
        
        Ini yang namanya Model-to-Schema conversion.
        Database Model punya field internal yang tidak perlu di-expose ke API.
        Schema Response hanya punya field yang clean untuk client.
        """
        return UserResponse(
            id=user.id,
            nama=user.nama,
            username=user.username,
            tempat_lahir=user.tempat_lahir,
            tanggal_lahir=user.tanggal_lahir,
            pangkat=user.pangkat,
            jabatan=user.jabatan,
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