"""User management endpoints with clean filter schemas."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.repositories.user import UserRepository
from src.repositories.role import RoleRepository
from src.services.user import UserService
from src.schemas.user import (
    UserCreate, UserUpdate, UserResponse, UserListResponse, UserSummary,
    UserUpdateRole, UserChangePassword, MessageResponse
)
from src.schemas.filters import (
    UserFilterParams, UsernameGenerationPreview, UsernameGenerationResponse
)
from src.auth.permissions import get_current_active_user, require_roles

router = APIRouter()

# Dependency for admin-only endpoints
admin_required = require_roles(["admin"])

# Dependency for admin and inspektorat endpoints
admin_or_inspektorat = require_roles(["admin", "inspektorat_1", "inspektorat_2", "inspektorat_3", "inspektorat_4"])


async def get_user_service(session: AsyncSession = Depends(get_db)) -> UserService:
    """Get user service dependency."""
    user_repo = UserRepository(session)
    role_repo = RoleRepository(session)
    return UserService(user_repo, role_repo)


@router.get("/me", response_model=UserResponse, summary="Get current user profile")
async def get_my_profile(
    current_user: dict = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get current user's own profile information.
    
    Returns detailed profile including roles and government-specific fields.
    """
    return await user_service.get_user_or_404(current_user["id"])


@router.put("/me", response_model=UserResponse, summary="Update current user profile")
async def update_my_profile(
    user_data: UserUpdate,
    current_user: dict = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Update current user's own profile information.
    
    Users can update their own:
    - full_name, tempat_lahir, tanggal_lahir, pangkat, jabatan, email
    - Cannot change username (auto-generated) or roles (admin-only)
    
    **Note**: 
    - Email can be set here for password reset functionality
    - Username will be regenerated if full_name or tanggal_lahir changes
    """
    return await user_service.update_user(current_user["id"], user_data)


@router.post("/me/change-password", response_model=MessageResponse, summary="Change current user password")
async def change_my_password(
    password_data: UserChangePassword,
    current_user: dict = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Change current user's password.
    
    - **current_password**: Current password for verification
    - **new_password**: New password (minimum 6 characters)
    
    Note: Default password for all users is @Kemendag123
    """
    return await user_service.change_password(current_user["id"], password_data)


@router.get("/", response_model=UserListResponse, summary="Get all users with comprehensive filters")
async def get_all_users(
    filters: UserFilterParams = Depends(),
    current_user: dict = Depends(admin_or_inspektorat),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get all users with pagination and comprehensive filters.
    
    **Accessible by**: Admin and Inspektorat roles
    
    **Query Parameters** (via UserFilterParams schema):
    - **page**: Page number (default: 1)
    - **size**: Items per page (default: 20, max: 100)
    - **search**: Search in full_name, username, tempat_lahir, pangkat, jabatan, email
    - **role_name**: Filter by specific role
    - **pangkat**: Filter by pangkat
    - **jabatan**: Filter by jabatan
    - **tempat_lahir**: Filter by tempat lahir
    - **has_email**: Filter by email status (true/false)
    - **is_active**: Filter by active status (true/false)
    - **min_age**: Minimum age filter (17-70)
    - **max_age**: Maximum age filter (17-70)
    
    **Examples**:
    - `GET /users?has_email=false` - Users without email
    - `GET /users?role_name=admin&is_active=true` - Active admin users
    - `GET /users?search=daffa&pangkat=penata` - Search with filters
    - `GET /users?min_age=25&max_age=40` - Users aged 25-40
    
    **Returns**: Paginated list with total count and page info
    """
    return await user_service.get_all_users_with_filters(filters)


@router.get("/by-role/{role_name}", response_model=list[UserSummary], summary="Get users by role")
async def get_users_by_role(
    role_name: str,
    current_user: dict = Depends(admin_or_inspektorat),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get all active users with specific role.
    
    **Accessible by**: Admin and Inspektorat roles
    
    Returns simplified user information for users with the specified role.
    """
    return await user_service.get_users_by_role(role_name)


@router.get("/statistics", summary="Get user statistics")
async def get_user_statistics(
    current_user: dict = Depends(admin_required),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get comprehensive user statistics.
    
    **Accessible by**: Admin only
    
    Returns:
    - Total active users
    - Users with/without email + completion rate
    - Users count by role
    - Users count by pangkat
    - Age distribution statistics
    """
    return await user_service.get_user_statistics()


@router.post("/preview-username", response_model=UsernameGenerationResponse, summary="Preview username generation")
async def preview_username_generation(
    preview_data: UsernameGenerationPreview,
    current_user: dict = Depends(admin_required),
    user_service: UserService = Depends(get_user_service)
):
    """
    Preview username generation from full_name and tanggal_lahir.
    
    **Accessible by**: Admin only
    
    **Format**: {nama_depan}{dd}{mm}{yyyy}
    
    **Example**:
    - Input: "Daffa Jatmiko", "2003-08-01"
    - Output: "daffa01082003"
    
    Shows what username would be generated and if it's available.
    Useful before creating a new user.
    """
    return await user_service.preview_username_generation(preview_data)


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Create new user (Admin only)")
async def create_user(
    user_data: UserCreate,
    current_user: dict = Depends(admin_required),
    user_service: UserService = Depends(get_user_service)
):
    """
    Create a new user.
    
    **Accessible by**: Admin only
    
    **Required fields**:
    - full_name (without titles/degrees)
    - tempat_lahir, tanggal_lahir, pangkat, jabatan
    - role_names (at least one role)
    
    **Optional fields**:
    - email (can be set later by user via PUT /users/me)
    
    **Auto-generated**:
    - username (format: nama_depan + ddmmyyyy)
    - password (@Kemendag123 for all users)
    
    **Validation**:
    - Full name must not contain titles (Dr., Ir., etc.)
    - Username will be auto-generated and must be unique
    - Email must be unique (if provided)
    - All specified roles must exist
    - Age must be between 17-70 years
    
    **Username Examples**:
    - "Daffa Jatmiko" + 01-08-2003 → "daffa01082003"
    - "Siti Rahayu" + 25-12-1990 → "siti25121990"
    """
    return await user_service.create_user(user_data)


@router.get("/{user_id}", response_model=UserResponse, summary="Get user by ID")
async def get_user(
    user_id: str,
    current_user: dict = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get user by UUID.
    
    **Access rules**:
    - Users can view their own profile
    - Admin and Inspektorat can view any user
    """
    # Check access permissions
    if (current_user["id"] != user_id and 
        not any(role in current_user.get("roles", []) 
               for role in ["admin", "inspektorat_1", "inspektorat_2", "inspektorat_3", "inspektorat_4"])):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this user's information"
        )
    
    return await user_service.get_user_or_404(user_id)


@router.put("/{user_id}", response_model=UserResponse, summary="Update user (Admin only)")
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: dict = Depends(admin_required),
    user_service: UserService = Depends(get_user_service)
):
    """
    Update user information.
    
    **Accessible by**: Admin only
    
    **Updatable fields**:
    - full_name, tempat_lahir, tanggal_lahir, pangkat, jabatan, email, is_active
    
    **Note**: 
    - Username will be regenerated if full_name or tanggal_lahir changes
    - Roles are updated via separate endpoint PUT /{user_id}/roles
    """
    return await user_service.update_user(user_id, user_data)


@router.put("/{user_id}/roles", response_model=UserResponse, summary="Update user roles (Admin only)")
async def update_user_roles(
    user_id: str,
    role_data: UserUpdateRole,
    current_user: dict = Depends(admin_required),
    user_service: UserService = Depends(get_user_service)
):
    """
    Update user roles.
    
    **Accessible by**: Admin only
    
    **Parameters**:
    - **role_names**: List of role names to assign (replaces existing roles)
    
    **Validation**:
    - All specified roles must exist
    - At least one role must be specified
    """
    return await user_service.update_user_roles(user_id, role_data)


@router.post("/{user_id}/reset-password", response_model=MessageResponse, summary="Reset user password (Admin only)")
async def reset_user_password(
    user_id: str,
    current_user: dict = Depends(admin_required),
    user_service: UserService = Depends(get_user_service)
):
    """
    Reset user password to default (@Kemendag123).
    
    **Accessible by**: Admin only
    
    Useful when user forgets password and doesn't have email set.
    """
    return await user_service.reset_user_password(user_id)


@router.post("/{user_id}/activate", response_model=UserResponse, summary="Activate user (Admin only)")
async def activate_user(
    user_id: str,
    current_user: dict = Depends(admin_required),
    user_service: UserService = Depends(get_user_service)
):
    """
    Activate user account.
    
    **Accessible by**: Admin only
    
    Sets user's is_active status to True.
    """
    return await user_service.activate_user(user_id)


@router.post("/{user_id}/deactivate", response_model=UserResponse, summary="Deactivate user (Admin only)")
async def deactivate_user(
    user_id: str,
    current_user: dict = Depends(admin_required),
    user_service: UserService = Depends(get_user_service)
):
    """
    Deactivate user account.
    
    **Accessible by**: Admin only
    
    Sets user's is_active status to False.
    
    **Protection**: Cannot deactivate the last active admin user.
    """
    return await user_service.deactivate_user(user_id)


@router.delete("/{user_id}", response_model=MessageResponse, summary="Delete user (Admin only)")
async def delete_user(
    user_id: str,
    current_user: dict = Depends(admin_required),
    user_service: UserService = Depends(get_user_service)
):
    """
    Soft delete user account.
    
    **Accessible by**: Admin only
    
    **Protection**: Cannot delete the last admin user.
    
    **Note**: This is a soft delete - user data is preserved but marked as deleted.
    """
    # Prevent admin from deleting themselves
    if current_user["id"] == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    return await user_service.delete_user(user_id)