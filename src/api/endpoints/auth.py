"""Authentication endpoints (simplified - nama as username) with Cookie Support."""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, BackgroundTasks
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
    request: Request,
    response: Response,  # 🔥 TAMBAH INI UNTUK COOKIE
    session: AsyncSession = Depends(get_db),
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
        # Execute login with response for cookies
        result = await auth_service.login(login_data, response)
        
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
    request: Request,
    response: Response,  # 🔥 TAMBAH INI UNTUK COOKIE
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Refresh access token using refresh token from cookie.
    
    Returns new access token with updated user information.
    """
    from src.utils.cookies import get_refresh_token_from_cookie
    
    # Get refresh token from cookie
    refresh_token = get_refresh_token_from_cookie(request)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found in cookie"
        )
    
    return await auth_service.refresh_token(refresh_token, response)


@router.post("/logout", response_model=MessageResponse, summary="Logout user")
async def logout(
    response: Response,  # 🔥 TAMBAH INI UNTUK COOKIE
    token: str = Depends(get_token_string),
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
    return await auth_service.logout(token, response)


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
    background_tasks: BackgroundTasks,  # ⭐ TAMBAH PARAMETER INI
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Request password reset token dengan BACKGROUND EMAIL SENDING.
    
    - **email**: User email address (must be set in profile first)
    
    **NEW FEATURE**: Email sending now runs in background for faster response!
    
    **Process**:
    1. Validate user and email ✅ (blocking)
    2. Generate and save reset token ✅ (blocking) 
    3. Schedule email sending 📧 (background)
    4. Return success response immediately 🚀
    
    **Performance**: Response time reduced from ~3s to ~200ms
    """
    import logging
    from src.utils.password import generate_password_reset_token, mask_email
    from src.core.config import settings
    from datetime import datetime, timedelta
    
    logger = logging.getLogger(__name__)
    
    user = await auth_service.user_repo.get_by_email(reset_data.email)
    
    # Always return success message to prevent email enumeration
    success_message = "Jika email tersebut terdaftar dan terkait dengan akun, link reset password telah dikirim"
    
    # Case 1: Email tidak ditemukan di database
    if not user:
        logger.warning(f"Reset password request for unregistered email: {mask_email(reset_data.email)}")
        return MessageResponse(message=success_message)
    
    # Case 2: User tidak aktif
    if not user.is_active:
        logger.warning(f"Reset password request for inactive user: {user.nama} ({mask_email(reset_data.email)})")
        return MessageResponse(message=success_message)
    
    # Case 3: User aktif tapi tidak punya email (edge case)
    if not user.has_email():
        logger.warning(f"Reset password request for user without email: {user.nama}")
        return MessageResponse(
            message="Akun user tidak memiliki email yang dikonfigurasi. Silakan hubungi administrator."
        )
    
    # Case 4: Semua validasi passed - process reset
    logger.info(f"Processing password reset for user: {user.nama} ({mask_email(user.email)})")
    
    # Generate reset token
    token = generate_password_reset_token()
    expires_at = datetime.utcnow() + timedelta(hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS)
    
    # Save token to database (BLOCKING - must complete before response)
    try:
        await auth_service.user_repo.create_password_reset_token(
            user.id,
            token,
            expires_at
        )
        logger.info(f"Password reset token created for user: {user.nama}")
    except Exception as e:
        logger.error(f"Failed to create password reset token for {mask_email(user.email)}: {str(e)}")
        return MessageResponse(
            message="Gagal memproses permintaan reset password. Silakan coba lagi nanti.",
            success=False
        )
    
    # 🚀 BACKGROUND EMAIL SENDING - PERUBAHAN UTAMA!
    logger.info(f"Scheduling background email for {mask_email(user.email)}")
    
    background_tasks.add_task(
        auth_service.email_service.send_password_reset_email,
        user.email,      # user_email
        user.nama,       # user_nama  
        token           # reset_token
    )
    
    # ✅ RETURN IMMEDIATELY - email sedang dikirim di background
    logger.info(f"Password reset response sent immediately, email processing in background")
    
    return MessageResponse(message=success_message)



@router.post("/confirm-password-reset", response_model=MessageResponse, summary="Confirm password reset")
async def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    background_tasks: BackgroundTasks,  # ⭐ TAMBAH PARAMETER INI
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Confirm password reset with token dengan BACKGROUND SUCCESS EMAIL.
    
    - **token**: Password reset token from email
    - **new_password**: New password (minimum 6 characters)
    
    **NEW FEATURE**: Success confirmation email now sent in background!
    
    Resets user password if token is valid and not expired (1 hour expiry).
    """
    import logging
    from src.utils.password import mask_email
    
    logger = logging.getLogger(__name__)
    
    # Get and validate token
    reset_token = await auth_service.user_repo.get_password_reset_token(reset_data.token)
    
    if not reset_token or not reset_token.is_valid():
        logger.warning(f"Invalid or expired reset token used: {reset_data.token[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token reset tidak valid atau kedaluwarsa"
        )
    
    # Get user
    user = await auth_service.user_repo.get_by_id(reset_token.user_id)
    if not user:
        logger.error(f"User not found for reset token: {reset_token.user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User tidak ditemukan"
        )
    
    # Check if new password is different from current
    from src.auth.jwt import verify_password, get_password_hash
    if verify_password(reset_data.new_password, user.hashed_password):
        logger.warning(f"User {user.nama} tried to reset with same password")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password baru harus berbeda dari password saat ini"
        )
    
    # Update password (BLOCKING - must complete)
    new_hashed_password = get_password_hash(reset_data.new_password)
    
    try:
        await auth_service.user_repo.update_password(user.id, new_hashed_password)
        logger.info(f"Password successfully updated for user: {user.nama} ({mask_email(user.email)})")
    except Exception as e:
        logger.error(f"Failed to update password for user {user.nama}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal memperbarui password. Silakan coba lagi."
        )
    
    # Mark token as used (BLOCKING)
    try:
        await auth_service.user_repo.use_password_reset_token(reset_data.token)
        logger.info(f"Reset token marked as used: {reset_data.token[:8]}...")
    except Exception as e:
        logger.error(f"Failed to mark reset token as used: {str(e)}")
        # Continue anyway, password is already updated
    
    # 🚀 BACKGROUND SUCCESS EMAIL - PERUBAHAN UTAMA!
    if user.has_email():
        logger.info(f"Scheduling background success email for {mask_email(user.email)}")
        
        background_tasks.add_task(
            auth_service.email_service.send_password_reset_success_email,
            user.email,    # user_email
            user.nama      # user_nama
        )
    
    # ✅ RETURN IMMEDIATELY - success email sedang dikirim di background
    logger.info(f"Password reset completed, success email processing in background")
    
    return MessageResponse(message="Reset password berhasil")


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