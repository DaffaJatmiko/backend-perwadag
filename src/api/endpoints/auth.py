"""Authentication endpoints (simplified - nama as username)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.repositories.user import UserRepository
from src.repositories.role import RoleRepository
from src.services.user import UserService
from src.services.auth import AuthService
from src.schemas.user import (
    UserLogin, Token, TokenRefresh, PasswordReset, PasswordResetConfirm,
    MessageResponse, UserResponse
)
from src.auth.permissions import get_current_active_user

router = APIRouter()


async def get_auth_service(session: AsyncSession = Depends(get_db)) -> AuthService:
    """Get auth service dependency."""
    user_repo = UserRepository(session)
    role_repo = RoleRepository(session)
    user_service = UserService(user_repo, role_repo)
    return AuthService(user_service, user_repo)


@router.post("/login", response_model=Token, summary="Login user")
async def login(
    login_data: UserLogin,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Login with nama (as username) and password.
    
    - **nama**: Nama lengkap (digunakan sebagai username)
    - **password**: User password (default: @Kemendag123)
    
    Returns JWT access token and refresh token along with user information.
    
    **Login Info**:
    - Username = Nama lengkap user (contoh: "Budi Santoso")
    - All users start with password: @Kemendag123
    - Case sensitive untuk nama
    
    **Example**:
    ```json
    {
      "nama": "Administrator Sistem",
      "password": "@Kemendag123"
    }
    ```
    """
    return await auth_service.login(login_data)


@router.post("/refresh", response_model=Token, summary="Refresh access token")
async def refresh_access_token(
    token_data: TokenRefresh,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Refresh access token using refresh token.
    
    - **refresh_token**: Valid refresh token
    
    Returns new access token with updated user information.
    """
    return await auth_service.refresh_token(token_data.refresh_token)


@router.post("/logout", response_model=MessageResponse, summary="Logout user")
async def logout(
    current_user: dict = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Logout current user.
    
    In JWT implementation, this is mainly handled client-side.
    """
    return await auth_service.logout()


# @router.get("/me", response_model=UserResponse, summary="Get current user info")
# async def get_current_user_info(
#     current_user: dict = Depends(get_current_active_user),
#     auth_service: AuthService = Depends(get_auth_service)
# ):
#     """
#     Get current authenticated user information.
    
#     Returns detailed user profile including roles.
#     """
#     return await auth_service.get_current_user_info(current_user["id"])


@router.get("/password-reset-eligibility", summary="Check password reset eligibility")
async def check_password_reset_eligibility(
    current_user: dict = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Check if current user is eligible for password reset.
    
    User must have email set before they can request password reset.
    
    **Response**:
    - `eligible`: true/false
    - `has_email`: true/false  
    - `email`: user email or null
    - `message`: explanation
    
    If user doesn't have email, they need to set it via PUT /users/me first.
    """
    return await auth_service.check_password_reset_eligibility(current_user["id"])


@router.post("/request-password-reset", response_model=MessageResponse, summary="Request password reset")
async def request_password_reset(
    reset_data: PasswordReset,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Request password reset token.
    
    - **email**: User email address (must be set in profile first)
    
    **Requirements**:
    1. User must have set email in their profile first (PUT /users/me)
    2. Email must be associated with an active account
    
    **Process**:
    1. If user hasn't set email → Contact administrator or set email first
    2. If email exists → Reset link sent to email
    3. Always returns success message to prevent email enumeration
    
    **Note**: Users can set email via PUT /users/me endpoint.
    """
    return await auth_service.request_password_reset(reset_data)


@router.post("/confirm-password-reset", response_model=MessageResponse, summary="Confirm password reset")
async def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Confirm password reset with token.
    
    - **token**: Password reset token from email
    - **new_password**: New password (minimum 6 characters)
    
    Resets user password if token is valid and not expired (1 hour expiry).
    """
    return await auth_service.confirm_password_reset(reset_data)


@router.get("/verify-token", summary="Verify JWT token")
async def verify_token(
    current_user: dict = Depends(get_current_active_user)
):
    """
    Verify if current JWT token is valid.
    
    Returns basic user info if token is valid.
    Useful for frontend to check token validity.
    """
    return {
        "valid": True,
        "user_id": current_user["id"],
        "nama": current_user["nama"],
        "roles": current_user["roles"],
        "message": "Token is valid"
    }


@router.get("/default-password-info", summary="Get default password info")
async def get_default_password_info(
    current_user: dict = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Get information about default password policy.
    
    **Accessible by**: Any authenticated user
    
    Returns information about the default password for reference.
    Admins get more detailed info including the actual password.
    """
    # Check if user is admin to show actual password
    is_admin = "admin" in current_user.get("roles", [])
    
    if is_admin:
        return await auth_service.get_default_password_info()
    else:
        return {
            "message": "Default password is set by administrator",
            "description": "All new users receive a default password",
            "recommendation": "Change your password after first login for security",
            "policy": "Set email address to enable password reset functionality"
        }