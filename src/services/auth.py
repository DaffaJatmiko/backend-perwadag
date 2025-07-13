"""Authentication service for government project (revised)."""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, status

from src.repositories.user import UserRepository
from src.services.user import UserService
from src.schemas.user import (
    UserLogin, Token, PasswordReset, PasswordResetConfirm, 
    MessageResponse, UserResponse
)
from src.auth.jwt import create_access_token, create_refresh_token, verify_token
from src.utils.password import generate_password_reset_token
from src.core.config import settings


class AuthService:
    """Service for authentication operations - simplified."""
    
    def __init__(self, user_service: UserService, user_repo: UserRepository):
        self.user_service = user_service
        self.user_repo = user_repo
        # No more role_repo needed!
    
    async def login(self, login_data: UserLogin) -> Token:
        """Login user with simplified role handling."""
        # Authenticate user
        user = await self.user_service.authenticate_user(
            login_data.username,  # atau login_data.nama jika schema pakai nama
            login_data.password
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
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
        
        # ✅ RETURN TOKEN RESPONSE
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_response
        )
    
    async def refresh_token(self, refresh_token: str) -> Token:
        """Refresh access token using refresh token."""
        try:
            # Verify refresh token
            payload = verify_token(refresh_token)
            
            # Check token type
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload"
                )
            
            # Get user
            user = await self.user_repo.get_by_id(user_id)
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive"
                )
            
            # Get user roles
            user_roles = [role.role.name for role in user.roles]
            
            # Create new access token
            token_data = {
                "sub": str(user.id),
                "username": user.username,
                "nama": user.nama,
                "roles": user_roles,
                "type": "access"
            }
            
            access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data=token_data,
                expires_delta=access_token_expires
            )
            
            # Build user response
            user_response = self.user_service._model_to_response(user)
            
            return Token(
                access_token=access_token,
                refresh_token=refresh_token,  # Keep the same refresh token
                token_type="bearer",
                expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                user=user_response
            )
            
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
    
    async def request_password_reset(self, reset_data: PasswordReset) -> MessageResponse:
        """Request password reset token - requires user to have email set."""
        user = await self.user_repo.get_by_email(reset_data.email)
        
        # Always return success message to prevent email enumeration
        success_message = "If the email exists and is associated with an account, a password reset link has been sent"
        
        if not user or not user.is_active:
            return MessageResponse(message=success_message)
        
        # Check if user has email set (should always be true if we found user by email)
        if not user.has_email():
            return MessageResponse(
                message="User account does not have email configured. Please contact administrator."
            )
        
        # Generate reset token
        token = generate_password_reset_token()
        expires_at = datetime.utcnow() + timedelta(hours=1)  # 1 hour expiry
        
        # Save token to database
        await self.user_repo.create_password_reset_token(
            user.id,
            token,
            expires_at
        )
        
        # TODO: Send email with reset link
        # For now, just log the token (remove in production)
        print(f"Password reset token for {user.nama} ({user.email}): {token}")
        print(f"Reset link: https://gov-app.pemda.go.id/reset-password?token={token}")
        
        return MessageResponse(message=success_message)
    
    async def confirm_password_reset(self, reset_data: PasswordResetConfirm) -> MessageResponse:
        """Confirm password reset with token."""
        # Get and validate token
        reset_token = await self.user_repo.get_password_reset_token(reset_data.token)
        
        if not reset_token or not reset_token.is_valid():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        # Get user
        user = await self.user_repo.get_by_id(reset_token.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if new password is different from current
        from src.auth.jwt import verify_password, get_password_hash
        if verify_password(reset_data.new_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from current password"
            )
        
        # Update password
        new_hashed_password = get_password_hash(reset_data.new_password)
        await self.user_repo.update_password(user.id, new_hashed_password)
        
        # Mark token as used
        await self.user_repo.use_password_reset_token(reset_data.token)
        
        return MessageResponse(message="Password reset successful")
    
    async def logout(self) -> MessageResponse:
        """Logout user (simple version without session management)."""
        # In a simple JWT implementation, logout is handled client-side
        # by discarding the token. In more advanced implementations,
        # you might want to blacklist the token.
        return MessageResponse(message="Logged out successfully")
    
    async def get_current_user_info(self, user_id: str) -> UserResponse:
        """Get current user information."""
        user = await self.user_service.get_user(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
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
                detail="User not found"
            )
        
        has_email = user.has_email()
        
        return {
            "eligible": has_email,
            "has_email": has_email,
            "email": user.email if has_email else None,
            "message": "User can request password reset" if has_email else "User must set email first before requesting password reset"
        }
    
    async def get_default_password_info(self) -> dict:
        """Get information about default password (for admin reference)."""
        return {
            "default_password": "@Kemendag123",
            "description": "Default password for all new users",
            "recommendation": "Users should change this password after first login",
            "policy": "Password must be changed if user wants to use password reset feature"
        }