"""Cookie utilities for secure authentication."""

from fastapi import Response, Request
from typing import Optional
from src.core.config import settings


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
    access_token_expires_minutes: int = None
) -> None:
    """
    Set HTTP-only secure cookies for authentication tokens.
    
    Args:
        response: FastAPI Response object
        access_token: JWT access token
        refresh_token: JWT refresh token
        access_token_expires_minutes: Access token expiry in minutes
    """
    if access_token_expires_minutes is None:
        access_token_expires_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    
    # Set access token cookie
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        max_age=access_token_expires_minutes * 60,  # Convert to seconds
        httponly=True,  # Prevent XSS attacks
        secure=not settings.DEBUG,    # Only send over HTTPS in production (HTTP allowed in dev)
        samesite="lax" if settings.DEBUG else "strict",  # Less strict in development
        path="/"
    )
    
    # Set refresh token cookie (longer expiry)
    response.set_cookie(
        key="refresh_token", 
        value=f"Bearer {refresh_token}",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,  # Convert to seconds
        httponly=True,  # Prevent XSS attacks
        secure=not settings.DEBUG,    # Only send over HTTPS in production (HTTP allowed in dev)
        samesite="lax" if settings.DEBUG else "strict",  # Less strict in development
        path="/"
    )


def clear_auth_cookies(response: Response) -> None:
    """
    Clear authentication cookies on logout.
    
    Args:
        response: FastAPI Response object
    """
    # Clear access token cookie
    response.set_cookie(
        key="access_token",
        value="",
        max_age=0,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax" if settings.DEBUG else "strict",
        path="/"
    )
    
    # Clear refresh token cookie
    response.set_cookie(
        key="refresh_token",
        value="",
        max_age=0,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax" if settings.DEBUG else "strict",
        path="/"
    )


def get_token_from_cookie(request: Request, cookie_name: str) -> Optional[str]:
    """
    Extract token from HTTP-only cookie.
    
    Args:
        request: FastAPI Request object
        cookie_name: Name of the cookie (access_token or refresh_token)
    
    Returns:
        Token string without Bearer prefix, or None if not found
    """
    cookie_value = request.cookies.get(cookie_name)
    if cookie_value and cookie_value.startswith("Bearer "):
        return cookie_value[7:]  # Remove "Bearer " prefix
    return None


def get_access_token_from_cookie(request: Request) -> Optional[str]:
    """Get access token from cookie."""
    return get_token_from_cookie(request, "access_token")


def get_refresh_token_from_cookie(request: Request) -> Optional[str]:
    """Get refresh token from cookie."""
    return get_token_from_cookie(request, "refresh_token")