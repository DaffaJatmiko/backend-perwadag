"""User management endpoints - FINAL WORKING VERSION."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.repositories.user import UserRepository
from src.services.user import UserService
from src.schemas.user import (
    UserCreate, UserUpdate, UserResponse, UserListResponse, UserSummary, 
    UserChangePassword, MessageResponse, PerwadagListResponse, PerwadagSummary
)
from src.schemas.filters import (
    UserFilterParams, UsernameGenerationPreview, UsernameGenerationResponse
)
from src.models.enums import UserRole
from src.auth.permissions import get_current_active_user, require_roles

router = APIRouter()

# Dependency for admin-only endpoints
admin_required = require_roles(["ADMIN"])

# Dependency for admin and inspektorat endpoints
admin_or_inspektorat = require_roles(["ADMIN", "INSPEKTORAT"])


async def get_user_service(session: AsyncSession = Depends(get_db)) -> UserService:
    """Get user service dependency - SIMPLIFIED."""
    user_repo = UserRepository(session)
    return UserService(user_repo)


@router.get("/me", response_model=UserResponse, summary="Get current user profile")
async def get_my_profile(
    current_user: dict = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get current user's own profile information.
    
    Returns detailed profile including role and government-specific fields.
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
    - nama, tempat_lahir, tanggal_lahir, pangkat, jabatan, email
    - Cannot change username (auto-generated) or role (admin-only)
    
    **Note**: 
    - Email can be set here for password reset functionality
    - Username will be regenerated if nama or tanggal_lahir changes
    """
    return await user_service.update_user(current_user["id"], user_data)


# @router.post("/me/change-password", response_model=MessageResponse, summary="Change current user password")
# async def change_my_password(
#     password_data: UserChangePassword,
#     current_user: dict = Depends(get_current_active_user),
#     user_service: UserService = Depends(get_user_service)
# ):
#     """
#     Change current user's password.
    
#     - **current_password**: Current password for verification
#     - **new_password**: New password (minimum 6 characters)
    
#     Note: Default password for all users is @Kemendag123
#     """
#     return await user_service.change_password(current_user["id"], password_data)


@router.get("/", response_model=UserListResponse, summary="Get all users with comprehensive filters")
async def get_all_users(
    filters: UserFilterParams = Depends(),
    current_user: dict = Depends(admin_or_inspektorat),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get all users with pagination and comprehensive filters.
    
    **Query Parameters**:
    - **search**: Search in nama, username, jabatan, email, inspektorat
    - **role**: Filter by role (admin/inspektorat/perwadag)
    - **inspektorat**: Filter by inspektorat
    - **jabatan**: Filter by jabatan
    - **has_email**: Filter by email status (true/false)
    - **is_active**: Filter by active status (true/false)
    
    **Examples**:
    - `GET /users?role=admin&is_active=true` - Active admin users
    - `GET /users?search=daffa&jabatan=kepala` - Search with filters
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
    
    **Available roles**: admin, inspektorat, perwadag
    
    Returns simplified user information for users with the specified role.
    """
    # Validate role
    try:
        role_enum = UserRole(role_name)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Available roles: {', '.join(UserRole.get_all_values())}"
        )
    
    users = await user_service.get_users_by_role(role_enum)
    return users


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
    Preview username generation from nama and inspektorat.
    
    **Format depends on role**:
    - admin/inspektorat: {nama_depan}_ir{nomor}
    - perwadag: extracted from nama
    
    **Examples**:
    - Input: "Daffa Jatmiko", "Inspektorat 1", role="admin"
    - Output: "daffa_ir1"
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
    
    **Required fields**:
    - nama (without titles/degrees)
    - jabatan
    - role (admin/inspektorat/perwadag)
    - inspektorat (required for admin/inspektorat roles)
    
    **Auto-generated**:
    - username (format depends on role)
      - admin/inspektorat: nama_depan_ir{nomor}
      - perwadag: extracted from nama (e.g., "ITPC Lagos" → "itpc_lagos")
    - password (@Kemendag123 for all users)
    
    **Username Examples**:
    - admin/inspektorat: "Daffa Jatmiko" + "Inspektorat 1" → "daffa_ir1"
    - perwadag: "ITPC Lagos – Nigeria" → "itpc_lagos"
    """
    return await user_service.create_user(user_data)


@router.get("/perwadag", response_model=PerwadagListResponse, summary="Search perwadag users")
async def search_perwadag_users(
    search: str = None,
    inspektorat: str = None, 
    is_active: bool = True,
    page: int = 1,
    size: int = 50,
    current_user: dict = Depends(get_current_active_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Search dan list perwadag users dengan pagination standar.
    
    **Accessible by**: All authenticated users
    
    **Query Parameters**:
    - **search**: Search term untuk nama perwadag atau inspektorat
    - **inspektorat**: Filter by specific inspektorat
    - **is_active**: Filter by active status (default: true)
    - **page**: Page number (default: 1)
    - **size**: Items per page (default: 50, max: 100)
    
    **Response format** (konsisten dengan endpoints lain):
    ```json
    {
      "items": [...],
      "total": 10,
      "page": 1,
      "size": 50,
      "pages": 1
    }
    ```
    
    **Response fields per item**:
    - **id**: User ID
    - **nama**: Nama perwadag/perwakilan dagang
    - **inspektorat**: Wilayah kerja inspektorat
    - **is_active**: Status aktif
    
    **Examples**:
    - `GET /users/perwadag?search=lagos` - Search perwadag dengan "lagos"
    - `GET /users/perwadag?inspektorat=Inspektorat 1&page=2` - Filter + pagination
    - `GET /users/perwadag?search=itpc&is_active=true&size=20` - Search + custom page size
    
    **Use case**: Untuk dropdown, autocomplete, atau list selection perwadag dengan pagination
    """
    # Validate page size
    if size > 100:
        size = 100
    
    return await user_service.search_perwadag_users(search, inspektorat, is_active, page, size)

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
    # Check access permissions - FIXED for single role system
    if (current_user["id"] != user_id and 
        current_user.get("role") not in ["admin", "inspektorat"]):
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
    - nama, tempat_lahir, tanggal_lahir, pangkat, jabatan, email, is_active, role, inspektorat
    
    **Note**: 
    - Username will be regenerated if nama or tanggal_lahir changes
    - If role changes to perwadag, inspektorat field becomes required
    - If role changes from perwadag, inspektorat field is auto-cleared
    """
    return await user_service.update_user(user_id, user_data)


# REMOVED: /{user_id}/roles endpoint - role is now part of user update


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

