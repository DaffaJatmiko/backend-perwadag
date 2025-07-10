"""Fixed authorization and permission checking - no circular import."""

from typing import List, Dict, Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.jwt import verify_token
from src.core.database import get_db


class JWTBearer(HTTPBearer):
    """Custom JWT Bearer handler."""
    
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
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
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid authorization code.",
            )


jwt_bearer = JWTBearer()


async def get_current_user(
    token: str = Depends(jwt_bearer), 
    session: AsyncSession = Depends(get_db)
) -> Dict:
    """Get the current authenticated user from JWT token."""
    # Import here to avoid circular import
    from src.repositories.user import UserRepository
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Verify and decode JWT token
        payload = verify_token(token)
        
        # Extract user ID from token
        user_id = payload.get("sub")
        if not user_id:
            raise credentials_exception

        # Get user from database to ensure they still exist and are active
        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(user_id)

        if not user:
            raise credentials_exception
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated"
            )

        # Extract roles from token and verify with database
        token_roles = payload.get("roles", [])
        
        # Get current user roles from database for verification
        user_roles = await user_repo.get_user_roles(user.id)
        current_roles = [role.name for role in user_roles]
        
        # Use current roles from database (more secure than trusting token)
        user_data = {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "nama": user.nama,
            "roles": current_roles,
            "is_active": user.is_active,
            "pangkat": user.pangkat,
            "jabatan": user.jabatan
        }

        return user_data

    except JWTError:
        raise credentials_exception
    except ValueError:
        raise credentials_exception
    except Exception:
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
    Dependency factory to require specific roles.
    
    Args:
        required_roles: List of role names that are allowed access
        
    Returns:
        Dependency function that checks user roles
    """
    async def _check_roles(
        current_user: Dict = Depends(get_current_active_user),
    ) -> Dict:
        user_roles = current_user.get("roles", [])
        
        # Check if user has any of the required roles
        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(required_roles)}",
            )
        
        return current_user
    
    return _check_roles


# Common role dependencies for easy reuse
admin_required = require_roles(["admin"])
inspektorat_required = require_roles(["inspektorat_1", "inspektorat_2", "inspektorat_3", "inspektorat_4"])
admin_or_inspektorat_required = require_roles([
    "admin", "inspektorat_1", "inspektorat_2", "inspektorat_3", "inspektorat_4"
])


# Utility functions for role checking (FIXED - tidak pakai await di luar async)
def has_role(user: Dict, role: str) -> bool:
    """Check if user has specific role."""
    user_roles = user.get("roles", [])
    return role in user_roles


def has_any_role(user: Dict, roles: List[str]) -> bool:
    """Check if user has any of the specified roles."""
    user_roles = user.get("roles", [])
    return any(role in user_roles for role in roles)


def is_admin(user: Dict) -> bool:
    """Check if user is admin."""
    return has_role(user, "admin")


def is_inspektorat(user: Dict) -> bool:
    """Check if user is from any inspektorat."""
    inspektorat_roles = ["inspektorat_1", "inspektorat_2", "inspektorat_3", "inspektorat_4"]
    return has_any_role(user, inspektorat_roles)


# Rate limiting by role (FIXED)
def get_rate_limit_by_role(user: Dict) -> int:
    """
    Get rate limit based on user role.
    Admins get higher limits, regular users get standard limits.
    """
    if is_admin(user):
        return 1000  # Higher limit for admins
    elif is_inspektorat(user):
        return 500   # Medium limit for inspektorat
    else:
        return 100   # Standard limit for other roles


# Security utilities
async def log_access_attempt(user: Dict, resource: str, success: bool = True):
    """
    Log access attempts for security monitoring.
    This could be enhanced to write to audit logs.
    """
    import logging
    
    logger = logging.getLogger(__name__)
    
    log_data = {
        "user_id": user.get("id"),
        "email": user.get("email"),
        "roles": user.get("roles", []),
        "resource": resource,
        "success": success,
        "pangkat": user.get("pangkat"),
        "jabatan": user.get("jabatan")
    }
    
    if success:
        logger.info(f"Access granted: {log_data}")
    else:
        logger.warning(f"Access denied: {log_data}")


# Government-specific role checks
def require_government_roles():
    """Require any government role (excludes external users if any)."""
    government_roles = [
        "admin", "inspektorat_1", "inspektorat_2", "inspektorat_3", "inspektorat_4",
        "perwadag", "bappeda", "dinas_kesehatan", "dinas_pendidikan", "dinas_sosial"
    ]
    return require_roles(government_roles)