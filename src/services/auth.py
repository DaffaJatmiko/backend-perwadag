"""Authentication service for government project (revised) with Cookie Support."""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, status, Response

from src.repositories.user import UserRepository
from src.services.user import UserService
from src.schemas.user import (
    UserLogin, Token, PasswordReset, PasswordResetConfirm, 
    MessageResponse, UserResponse
)
from src.auth.jwt import create_access_token, create_refresh_token, verify_token
from src.services.email import EmailService
from src.utils.password import generate_password_reset_token, mask_email
from src.utils.cookies import set_auth_cookies, clear_auth_cookies
from src.core.config import settings


class AuthService:
    """Service for authentication operations - simplified."""
    
    def __init__(self, user_service: UserService, user_repo: UserRepository):
        self.user_service = user_service
        self.user_repo = user_repo
        self.email_service = EmailService()  
        # No more role_repo needed!
    

    async def login(self, login_data: UserLogin, response: Response) -> Token:
        """Login user with simplified role handling."""
        # Authenticate user
        user = await self.user_service.authenticate_user(
            login_data.username,  # atau login_data.nama jika schema pakai nama
            login_data.password
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Username atau password salah",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create token data dengan single role (SIMPLIFIED!)
        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "nama": user.nama,
            "role": user.role.value,  # Single role instead of array
            "type": "access"
        }
        
        refresh_token_data = {
            "sub": str(user.id),
            "type": "refresh"
        }
        
        # ✅ CREATE TOKENS (match your existing JWT functions)
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data=token_data,
            expires_delta=access_token_expires
        )
        
        # ✅ Call refresh token WITHOUT expires_delta (match your JWT function signature)
        refresh_token = create_refresh_token(data=refresh_token_data)
        
        # ✅ BUILD USER RESPONSE
        # Check if method exists, otherwise use alternative
        try:
            user_response = self.user_service._model_to_response(user)
        except AttributeError:
            # Fallback to direct conversion
            user_response = UserResponse.from_user_model(user)
        
        # 🔥 TAMBAHAN: Clear logout flag setelah login berhasil
        from src.core.redis import redis_clear_role_changed
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            await redis_clear_role_changed(str(user.id))
            logger.info(f"Logout flag cleared for user {user.id}")
        except Exception as e:
            logger.warning(f"Failed to clear logout flag: {e}")
            # Jangan gagalkan login jika Redis error
        
        # ✅ SET COOKIES INSTEAD OF RETURNING TOKENS
        set_auth_cookies(
            response=response,
            access_token=access_token,
            refresh_token=refresh_token,
            access_token_expires_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        
        # ✅ RETURN TOKEN RESPONSE WITHOUT ACTUAL TOKENS (for backward compatibility)
        return Token(
            access_token="",  # Empty - token is in cookie
            refresh_token="",  # Empty - token is in cookie  
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_response
        )
    
    async def refresh_token(self, refresh_token: str, response: Response) -> Token:
        """Refresh access token dengan blacklist check."""
        from src.core.redis import redis_is_token_blacklisted, redis_is_role_changed
        
        try:
            # STEP 1: Check if refresh token is blacklisted
            is_blacklisted = await redis_is_token_blacklisted(refresh_token)
            if is_blacklisted:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token sudah tidak valid"
                )
            
            # STEP 2: Verify refresh token
            payload = verify_token(refresh_token)
            
            # Check token type
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Jenis token tidak valid"
                )
            
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Payload token tidak valid"
                )
            
            # STEP 3: Check role changes
            role_changed = await redis_is_role_changed(user_id)
            if role_changed:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Sesi telah berakhir, silahkan login ulang"
                )
            
            # STEP 4: Get user dan generate new tokens
            user = await self.user_repo.get_by_id(user_id)
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User tidak ditemukan atau tidak aktif"
                )
            
            # Generate new access token dengan role terbaru dari database
            user_role = user.role.value
            token_data = {
                "sub": str(user.id),
                "username": user.username,
                "nama": user.nama,
                "role": user_role,  # Role terbaru dari DB
                "type": "access"
            }
            
            access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data=token_data,
                expires_delta=access_token_expires
            )
            
            user_response = UserResponse.from_user_model(user)
            
            # ✅ SET NEW ACCESS TOKEN COOKIE
            set_auth_cookies(
                response=response,
                access_token=access_token,
                refresh_token=refresh_token,  # Keep same refresh token
                access_token_expires_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
            
            return Token(
                access_token="",  # Empty - token is in cookie
                refresh_token="",  # Empty - token is in cookie
                token_type="bearer",
                expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                user=user_response
            )
            
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token tidak valid"
            )
    
    async def request_password_reset(self, reset_data: PasswordReset) -> MessageResponse:
        """Request password reset token dengan proper email validation."""
        import logging
        logger = logging.getLogger(__name__)
        
        user = await self.user_repo.get_by_email(reset_data.email)
        
        # Always return success message to prevent email enumeration
        success_message = "Jika email tersebut terdaftar dan terkait dengan akun, link reset password telah dikirim"
        
        # Case 1: Email tidak ditemukan di database
        if not user:
            logger.warning(f"Reset password diminta untuk email yang tidak terdaftar: {mask_email(reset_data.email)}")
            return MessageResponse(message=success_message)
        
        # Case 2: User tidak aktif
        if not user.is_active:
            logger.warning(f"Reset password diminta untuk user tidak aktif: {user.nama} ({mask_email(reset_data.email)})")
            return MessageResponse(message=success_message)
        
        # Case 3: User aktif tapi tidak punya email (edge case - seharusnya tidak terjadi)
        if not user.has_email():
            logger.warning(f"Reset password diminta untuk user tanpa email: {user.nama}")
            # Return specific error karena ini edge case
            return MessageResponse(
                message="Akun user tidak memiliki email yang dikonfigurasi. Silakan hubungi administrator."
            )
        
        # Case 4: Semua validasi passed - process reset
        logger.info(f"Memproses reset password untuk user: {user.nama} ({mask_email(user.email)})")
        
        # Generate reset token
        token = generate_password_reset_token()
        expires_at = datetime.utcnow() + timedelta(hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS)
        
        # Save token to database
        try:
            await self.user_repo.create_password_reset_token(
                user.id,
                token,
                expires_at
            )
            logger.info(f"Token reset password dibuat untuk user: {user.nama}")
        except Exception as e:
            logger.error(f"Gagal membuat token reset password untuk {mask_email(user.email)}: {str(e)}")
            return MessageResponse(
                message="Gagal memproses permintaan reset password. Silakan coba lagi nanti.",
                success=False
            )
        
        # Send email with reset link
        try:
            email_sent = await self.email_service.send_password_reset_email(
                user_email=user.email,
                user_nama=user.nama,
                reset_token=token
            )
            
            if email_sent:
                logger.info(f"Email reset password berhasil dikirim ke {mask_email(user.email)}")
            else:
                logger.error(f"Gagal mengirim email reset password ke {mask_email(user.email)}")
                # Still return success message for security
                
        except Exception as e:
            logger.error(f"Exception saat mengirim email reset password ke {mask_email(user.email)}: {str(e)}")
            # Still return success message for security
        
        return MessageResponse(message=success_message)
    
    async def confirm_password_reset(self, reset_data: PasswordResetConfirm) -> MessageResponse:
        """Confirm password reset with token dan send success email."""
        import logging
        logger = logging.getLogger(__name__)
        
        # Get and validate token
        reset_token = await self.user_repo.get_password_reset_token(reset_data.token)
        
        if not reset_token or not reset_token.is_valid():
            logger.warning(f"Token reset tidak valid atau kedaluwarsa digunakan: {reset_data.token[:8]}...")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token reset tidak valid atau kedaluwarsa"
            )
        
        # Get user
        user = await self.user_repo.get_by_id(reset_token.user_id)
        if not user:
            logger.error(f"User tidak ditemukan untuk token reset: {reset_token.user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User tidak ditemukan"
            )
        
        # Check if new password is different from current
        from src.auth.jwt import verify_password, get_password_hash
        if verify_password(reset_data.new_password, user.hashed_password):
            logger.warning(f"User {user.nama} mencoba reset password dengan password yang sama")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password baru harus berbeda dari password saat ini"
            )
        
        # Update password
        new_hashed_password = get_password_hash(reset_data.new_password)
        
        try:
            await self.user_repo.update_password(user.id, new_hashed_password)
            logger.info(f"Password berhasil diperbarui untuk user: {user.nama} ({mask_email(user.email)})")
        except Exception as e:
            logger.error(f"Gagal memperbarui password untuk user {user.nama}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Gagal memperbarui password. Silakan coba lagi."
            )
        
        # Mark token as used
        try:
            await self.user_repo.use_password_reset_token(reset_data.token)
            logger.info(f"Token reset ditandai sebagai sudah digunakan: {reset_data.token[:8]}...")
        except Exception as e:
            logger.error(f"Gagal menandai token reset sebagai sudah digunakan: {str(e)}")
            # Continue anyway, password is already updated
        
        # Send success confirmation email
        if user.has_email():
            try:
                email_sent = await self.email_service.send_password_reset_success_email(
                    user_email=user.email,
                    user_nama=user.nama
                )
                
                if email_sent:
                    logger.info(f"Email konfirmasi reset password dikirim ke {mask_email(user.email)}")
                else:
                    logger.error(f"Gagal mengirim email konfirmasi ke {mask_email(user.email)}")
                    # Don't fail the whole operation if email fails
                    
            except Exception as e:
                logger.error(f"Exception saat mengirim email konfirmasi ke {mask_email(user.email)}: {str(e)}")
                # Don't fail the whole operation if email fails
        
        return MessageResponse(message="Reset password berhasil")
    
    async def logout(self, token: str, response: Response) -> MessageResponse:
        """Logout user - invalidate ALL tokens untuk user ini."""
        import time
        from src.core.redis import redis_blacklist_token, redis_mark_role_changed
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            # Decode current token (bisa access atau refresh)
            payload = verify_token(token)
            user_id = payload.get('sub')
            token_type = payload.get('type', 'access')
            
            # Calculate remaining time untuk current token
            exp_time = payload.get('exp', 0)
            current_time = time.time()
            remaining_seconds = int(exp_time - current_time)
            
            # Blacklist current token jika masih valid
            if remaining_seconds > 0:
                success = await redis_blacklist_token(token, remaining_seconds)
                if success:
                    logger.info(f"Token ({token_type}) blacklisted for {remaining_seconds} seconds for user {user_id}")
            
            # Note: Only blacklist current token, don't mark role as changed
            # Role change marking should only happen when role actually changes
            logger.info(f"Token {token_type} invalidated for user {user_id}")
            
            # ✅ CLEAR COOKIES
            clear_auth_cookies(response)
            logger.info(f"Auth cookies cleared for user {user_id}")
            
            logger.info(f"User {user_id} logged out successfully")
            return MessageResponse(message="Logout berhasil")
            
        except Exception as e:
            logger.warning(f"Logout attempt: {str(e)}")
            return MessageResponse(message="Logout berhasil")

    async def force_logout_user(self, user_id: str) -> MessageResponse:
        """Force logout user by marking role as changed (admin only)."""
        from src.core.redis import redis_mark_role_changed
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            # Mark user for forced re-login
            success = await redis_mark_role_changed(user_id, ttl_seconds=86400)
            
            if success:
                logger.info(f"User {user_id} forced to logout by admin")
                return MessageResponse(message="User berhasil di-force logout")
            else:
                logger.error(f"Failed to force logout user {user_id}")
                return MessageResponse(message="Failed to force logout user")
                
        except Exception as e:
            logger.error(f"Error during force logout: {e}")
            return MessageResponse(message="Failed to force logout user")
    
    async def get_current_user_info(self, user_id: str) -> UserResponse:
        """Get current user information."""
        user = await self.user_service.get_user(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User tidak ditemukan"
            )
        return user
    
    async def validate_user_access(self, user_id: str, required_roles: Optional[list] = None) -> bool:
        """Validate if user has required access."""
        user = await self.user_repo.get_by_id(user_id)
        
        if not user or not user.is_active:
            return False
        
        if required_roles:
            user_roles = [role.role.name for role in user.roles]
            return any(role in user_roles for role in required_roles)
        
        return True
    
    async def check_password_reset_eligibility(self, user_id: str) -> dict:
        """Check if user is eligible for password reset."""
        user = await self.user_repo.get_by_id(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User tidak ditemukan"
            )
        
        has_email = user.has_email()
        
        return {
            "eligible": has_email,
            "has_email": has_email,
            "email": user.email if has_email else None,
            "message": "User dapat meminta reset password" if has_email else "User harus mengatur email terlebih dahulu sebelum meminta reset password"
        }
    
    async def get_default_password_info(self) -> dict:
        """Get information about default password (for admin reference)."""
        return {
            "default_password": "@Kemendag123",
            "description": "Password default untuk semua user baru",
            "recommendation": "User harus mengubah password ini setelah login pertama",
            "policy": "Password harus diubah jika user ingin menggunakan fitur reset password"
        }