"""Fixed authorization and permission checking - SINGLE ROLE SYSTEM with Cookie Support."""

from typing import List, Dict, Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.jwt import verify_token
from src.core.database import get_db
from src.utils.cookies import get_access_token_from_cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

logger = logging.getLogger(__name__)


class JWTBearer(HTTPBearer):
    """Custom JWT Bearer handler with cookie support."""
    
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        # First try to get token from Authorization header
        try:
            credentials: HTTPAuthorizationCredentials = await super(
                JWTBearer, self
            ).__call__(request)
            
            if credentials:
                if not credentials.scheme == "Bearer":
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Invalid authentication scheme.",
                    )
                return credentials.credentials
        except HTTPException:
            # If Authorization header fails, try cookie
            token = get_access_token_from_cookie(request)
            if token:
                return token
            
            # If both fail and auto_error is True, raise exception
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated. Token required in Authorization header or cookie.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None


jwt_bearer = JWTBearer()

async def get_token_string(token: str = Depends(jwt_bearer)) -> str:
    """Extract token string from JWT bearer."""
    return token


async def get_current_user(
    token: str = Depends(jwt_bearer), 
    session: AsyncSession = Depends(get_db)
) -> Dict:
    """Get the current authenticated user from JWT token with blacklist and role change detection."""
    # Import Redis functions
    from src.core.redis import redis_is_token_blacklisted, redis_is_role_changed
    
    # Import here to avoid circular import
    from src.repositories.user import UserRepository
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # STEP 1: Check if token is blacklisted
        is_blacklisted = await redis_is_token_blacklisted(token)
        if is_blacklisted:
            logger.info("Blacklisted token used")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token sudah tidak valid",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # STEP 2: Verify and decode JWT token
        payload = verify_token(token)
        
        # Extract user ID from token
        user_id = payload.get("sub")
        if not user_id:
            raise credentials_exception

        # STEP 3: Check if user role has changed
        role_changed = await redis_is_role_changed(user_id)
        if role_changed:
            logger.info(f"User {user_id} role changed, forcing re-login")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Role berubah, silakan login ulang",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # STEP 4: Get user from database to ensure they still exist and are active
        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(user_id)

        if not user:
            raise credentials_exception
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated"
            )

        # STEP 5: Build user data response
        user_role = user.role.value  # Get from enum: "ADMIN", "INSPEKTORAT", "PERWADAG"
        
        user_data = {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "nama": user.nama,
            "role": user_role,           # Single role string
            "roles": [user_role],        # Array with single role for compatibility
            "is_active": user.is_active,
            "jabatan": user.jabatan,
            "inspektorat": user.inspektorat
        }

        return user_data

    except JWTError:
        raise credentials_exception
    except ValueError:
        raise credentials_exception
    except HTTPException:
        # Re-raise HTTP exceptions (blacklist, role change, etc.)
        raise
    except Exception as e:
        # Add logging for debugging
        logger.error(f"Authentication error: {str(e)}")
        raise credentials_exception


async def get_current_active_user(
    current_user: Dict = Depends(get_current_user),
) -> Dict:
    """Ensure the current user is active."""
    if not current_user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="User account is deactivated"
        )
    return current_user


def require_roles(required_roles: List[str]):
    """
    Dependency factory to require specific roles - SINGLE ROLE SYSTEM.
    
    Args:
        required_roles: List of role names that are allowed access
        
    Returns:
        Dependency function that checks user roles
    """
    async def _check_roles(
        current_user: Dict = Depends(get_current_active_user),
    ) -> Dict:
        # ✅ FIXED: Check single role instead of array
        user_role = current_user.get("role")
        
        # Check if user has any of the required roles
        if user_role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(required_roles)}. Your role: {user_role}",
            )
        
        return current_user
    
    return _check_roles


# Common role dependencies for easy reuse - UPDATED FOR YOUR ENUMS
admin_required = require_roles(["ADMIN"])
inspektorat_required = require_roles(["INSPEKTORAT"]) 
perwadag_required = require_roles(["PERWADAG"])
admin_or_inspektorat_required = require_roles(["ADMIN", "INSPEKTORAT"])


# Utility functions for role checking - FIXED FOR SINGLE ROLE
def has_role(user: Dict, role: str) -> bool:
    """Check if user has specific role - SINGLE ROLE SYSTEM."""
    user_role = user.get("role")
    return user_role == role


def has_any_role(user: Dict, roles: List[str]) -> bool:
    """Check if user has any of the specified roles - SINGLE ROLE SYSTEM."""
    user_role = user.get("role")
    return user_role in roles


def is_admin(user: Dict) -> bool:
    """Check if user is admin."""
    return has_role(user, "ADMIN")


def is_inspektorat(user: Dict) -> bool:
    """Check if user is inspektorat."""
    return has_role(user, "INSPEKTORAT")


def is_perwadag(user: Dict) -> bool:
    """Check if user is perwadag."""
    return has_role(user, "PERWADAG")

def is_pimpinan(user: Dict) -> bool:
    """Check if user is pimpinan."""
    return has_role(user, "PIMPINAN")


# Rate limiting by role - FIXED FOR SINGLE ROLE
def get_rate_limit_by_role(user: Dict) -> int:
    """Get rate limit based on user role - SINGLE ROLE SYSTEM."""
    user_role = user.get("role")
    
    if user_role == "ADMIN":
        return 1000  # Higher limit for admins
    elif user_role in ["PIMPINAN", "INSPEKTORAT"]:  # UBAH BARIS INI
        return 500   # Medium limit for pimpinan and inspektorat
    elif user_role == "PERWADAG":
        return 300   # Medium limit for perwadag
    else:
        return 100   # Standard limit for other roles

# Security utilities
async def log_access_attempt(user: Dict, resource: str, success: bool = True):
    """
    Log access attempts for security monitoring.
    """
    import logging
    
    logger = logging.getLogger(__name__)
    
    log_data = {
        "user_id": user.get("id"),
        "email": user.get("email"),
        "role": user.get("role"),        # Single role
        "resource": resource,
        "success": success,
        # "pangkat": user.get("pangkat"),
        "jabatan": user.get("jabatan")
    }
    
    if success:
        logger.info(f"Access granted: {log_data}")
    else:
        logger.warning(f"Access denied: {log_data}")


# Government-specific role checks - UPDATED FOR YOUR SYSTEM
def require_government_roles():
    """Require any government role."""
    government_roles = ["ADMIN", "INSPEKTORAT", "PIMPINAN", "PERWADAG"] 
    return require_roles(government_roles)