"""Authentication endpoints (simplified - nama as username)."""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.repositories.user import UserRepository
from src.repositories.log_activity import LogActivityRepository
from src.schemas.log_activity import LogActivityCreate
from datetime import datetime
from src.services.user import UserService
from src.services.auth import AuthService
from src.schemas.user import (
    UserLogin, Token, TokenRefresh, PasswordReset, PasswordResetConfirm,
    MessageResponse, UserResponse, UserChangePassword
)
from src.auth.permissions import get_current_active_user, admin_required, get_token_string

import logging

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_auth_service(session: AsyncSession = Depends(get_db)) -> AuthService:
    """Get auth service dependency - SIMPLIFIED."""
    user_repo = UserRepository(session)
    user_service = UserService(user_repo)  # No more role_repo!
    return AuthService(user_service, user_repo)


@router.post("/login", response_model=Token, summary="Login user")
async def login(
    login_data: UserLogin,
    request: Request,  # 🔥 TAMBAH INI
    session: AsyncSession = Depends(get_db),  # 🔥 TAMBAH INI
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Login with nama (as username) and password.
    
    - **nama**: Nama lengkap (digunakan sebagai username)
    - **password**: User password (default: @Kemendag123)
    
    Returns JWT access token and refresh token along with user information.
    """
    
    # 🔥 TAMBAH: Get IP address
    def get_client_ip(request: Request) -> str:
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        return request.client.host if request.client else "unknown"
    
    ip_address = get_client_ip(request)
    
    try:
        # Execute login
        result = await auth_service.login(login_data)
        
        # 🔥 TAMBAH: Log successful login
        try:
            from src.core.config import settings
            base_url = settings.API_BASE_URL.rstrip('/')
            full_url = f"{base_url}{request.url.path}"
            
            log_repo = LogActivityRepository(session)
            log_data = LogActivityCreate(
                user_id=result.user.id,  # From login result
                method="POST",
                url=full_url,
                activity="User login",
                date=datetime.utcnow(),
                user_name=result.user.nama,
                ip_address=ip_address,
                response_status=200
            )
            await log_repo.create(log_data)
            await session.commit()
        except Exception as e:
            # Don't break login if logging fails
            logger.error(f"Failed to log login activity: {e}")
        
        return result
        
    except HTTPException as e:
        # 🔥 TAMBAH: Log failed login attempt
        try:
            from src.core.config import settings
            base_url = settings.API_BASE_URL.rstrip('/')
            full_url = f"{base_url}{request.url.path}"
            
            log_repo = LogActivityRepository(session)
            log_data = LogActivityCreate(
                user_id=None,  # No user for failed login
                method="POST", 
                url=full_url,
                activity="Failed login attempt",
                date=datetime.utcnow(),
                user_name=f"Failed login: {login_data.nama}",
                ip_address=ip_address,
                response_status=e.status_code
            )
            await log_repo.create(log_data)
            await session.commit()
        except Exception as log_error:
            logger.error(f"Failed to log failed login: {log_error}")
        
        # Re-raise original exception
        raise e


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
    token: str = Depends(get_token_string),  # Tambahkan ini
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Logout current user dengan token blacklist.
    
    **Process**:
    1. Extract token dari Authorization header
    2. Add token ke Redis blacklist dengan TTL = remaining token life
    3. Token menjadi invalid untuk semua request selanjutnya
    
    **Security**:
    - Token benar-benar invalid setelah logout (tidak seperti client-side logout)
    - Stolen token tidak bisa digunakan setelah legitimate user logout
    """
    return await auth_service.logout(token)


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

@router.post("/change-password", response_model=MessageResponse, summary="Change user password")
async def change_password(
    password_data: UserChangePassword,
    current_user: dict = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Change current user's password.
    
    *Requires*: Valid JWT token
    
    - *current_password*: Current password
    - *new_password*: New password (minimum 6 characters)
    
    *Process*:
    1. Verify current password is correct
    2. Ensure new password is different from current
    3. Update password in database
    
    *Security*:
    - User must be authenticated with valid token
    - Current password must be verified before change
    - New password must meet minimum requirements
    """
    user_service = UserService(UserRepository(auth_service.user_repo.session))
    return await user_service.change_password(current_user["id"], password_data)

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