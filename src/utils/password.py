"""Enhanced password utilities for reset functionality."""

import secrets
import string
from src.core.config import settings


def generate_password_reset_token(length: int = None) -> str:
    """
    Generate secure random token for password reset.
    
    Args:
        length: Token length (default from settings)
    
    Returns:
        Secure random token string
    """
    if length is None:
        length = settings.PASSWORD_RESET_TOKEN_LENGTH
    
    # Use URL-safe characters (letters, numbers, -, _)
    alphabet = string.ascii_letters + string.digits + '-_'
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_reset_link(token: str) -> str:
    """
    Generate complete reset link with token.
    
    Args:
        token: Password reset token
    
    Returns:
        Complete reset URL
    """
    base_url = settings.EMAIL_RESET_URL_BASE.rstrip('/')
    return f"{base_url}?token={token}"


def mask_email(email: str) -> str:
    """
    Mask email for logging purposes.
    
    Args:
        email: Email address to mask
    
    Returns:
        Masked email (e.g., "u***@example.com")
    """
    if not email or '@' not in email:
        return "***@***.***"
    
    local, domain = email.split('@', 1)
    
    if len(local) <= 2:
        masked_local = local[0] + '*'
    else:
        masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
    
    return f"{masked_local}@{domain}"