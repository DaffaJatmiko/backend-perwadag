"""Authorization and permission checking for government project."""

from typing import List, Dict, Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.jwt import verify_token
from src.core.database import get_db
from src.repositories.user import UserRepository


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
        user = await user_repo.get_by_id(int(user_id))

        if not user:
            raise credentials_exception
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated"
            )

        # Extract roles from token (for performance) and verify with database
        token_roles = payload.get("roles", [])
        
        # Get current user roles from database for verification
        user_roles = await user_repo.get_user_roles(user.id)
        current_roles = [role.name for role in user_roles]
        
        # Use current roles from database (more secure than trusting token)
        user_data = {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": user.full_name,
            "roles": current_roles,
            "is_active": user.is_active,
            "nip": user.nip,
            "unit_kerja": user.unit_kerja,
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


def require_any_role():
    """Require user to have at least one role (any authenticated user)."""
    async def _check_any_role(
        current_user: Dict = Depends(get_current_active_user),
    ) -> Dict:
        user_roles = current_user.get("roles", [])
        
        if not user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. User must have at least one role assigned.",
            )
        
        return current_user
    
    return _check_any_role


def require_same_user_or_roles(allowed_roles: List[str]):
    """
    Require either the same user or specific roles.
    Used for endpoints where users can access their own data or admins can access any data.
    
    Args:
        allowed_roles: List of role names that can access any user's data
        
    Returns:
        Dependency function that checks user permissions
    """
    async def _check_same_user_or_roles(
        user_id: int,
        current_user: Dict = Depends(get_current_active_user),
    ) -> Dict:
        user_roles = current_user.get("roles", [])
        
        # Allow if same user
        if current_user["id"] == user_id:
            return current_user
        
        # Allow if user has required roles
        if any(role in user_roles for role in allowed_roles):
            return current_user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only access your own data or need appropriate permissions.",
        )
    
    return _check_same_user_or_roles


# Common role dependencies for easy reuse
admin_required = require_roles(["admin"])
inspektorat_required = require_roles(["inspektorat_1", "inspektorat_2", "inspektorat_3", "inspektorat_4"])
admin_or_inspektorat_required = require_roles([
    "admin", "inspektorat_1", "inspektorat_2", "inspektorat_3", "inspektorat_4"
])


# Government-specific role checks
def require_government_roles():
    """Require any government role (excludes external users if any)."""
    government_roles = [
        "admin", "inspektorat_1", "inspektorat_2", "inspektorat_3", "inspektorat_4",
        "perwadag", "bappeda", "dinas_kesehatan", "dinas_pendidikan", "dinas_sosial"
    ]
    return require_roles(government_roles)


def require_admin_or_same_unit(unit_field: str = "unit_kerja"):
    """
    Require admin role or same unit_kerja.
    Useful for unit-specific data access.
    
    Args:
        unit_field: Field name to compare (default: "unit_kerja")
    """
    async def _check_admin_or_same_unit(
        target_unit: str,
        current_user: Dict = Depends(get_current_active_user),
    ) -> Dict:
        user_roles = current_user.get("roles", [])
        
        # Admin can access everything
        if "admin" in user_roles:
            return current_user
        
        # Check if same unit
        user_unit = current_user.get(unit_field)
        if user_unit and user_unit == target_unit:
            return current_user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only access data from your unit or need admin permissions.",
        )
    
    return _check_admin_or_same_unit


# Utility functions for role checking
async def has_role(user: Dict, role: str) -> bool:
    """Check if user has specific role."""
    user_roles = user.get("roles", [])
    return role in user_roles


async def has_any_role(user: Dict, roles: List[str]) -> bool:
    """Check if user has any of the specified roles."""
    user_roles = user.get("roles", [])
    return any(role in user_roles for role in roles)


async def is_admin(user: Dict) -> bool:
    """Check if user is admin."""
    return await has_role(user, "admin")


async def is_inspektorat(user: Dict) -> bool:
    """Check if user is from any inspektorat."""
    inspektorat_roles = ["inspektorat_1", "inspektorat_2", "inspektorat_3", "inspektorat_4"]
    return await has_any_role(user, inspektorat_roles)


# Optional: Rate limiting by role
def get_rate_limit_by_role(user: Dict) -> int:
    """
    Get rate limit based on user role.
    Admins get higher limits, regular users get standard limits.
    """
    if await is_admin(user):
        return 1000  # Higher limit for admins
    elif await is_inspektorat(user):
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
        "unit_kerja": user.get("unit_kerja")
    }
    
    if success:
        logger.info(f"Access granted: {log_data}")
    else:
        logger.warning(f"Access denied: {log_data}")


# Decorator for endpoint-level security logging
def log_endpoint_access(resource_name: str):
    """
    Decorator to log access to specific endpoints.
    Usage: @log_endpoint_access("user_management")
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract current_user from kwargs if present
            current_user = kwargs.get("current_user")
            if current_user:
                await log_access_attempt(current_user, resource_name, True)
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator