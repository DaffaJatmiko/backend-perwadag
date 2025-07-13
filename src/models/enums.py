"""Enums untuk database models - MATCH DATABASE UPPERCASE."""

from enum import Enum


class UserRole(str, Enum):
    """User role enum yang match dengan database UPPERCASE values."""
    ADMIN = "ADMIN"           # Database: ADMIN
    INSPEKTORAT = "INSPEKTORAT"  # Database: INSPEKTORAT
    PERWADAG = "PERWADAG"     # Database: PERWADAG
    
    @classmethod
    def get_all_values(cls):
        """Get all role values as list."""
        return [role.value for role in cls]
    
    @classmethod
    def is_valid_role(cls, role: str) -> bool:
        """Check if role is valid."""
        return role in cls.get_all_values()
    
    @classmethod
    def get_lowercase_values(cls):
        """Get lowercase values for API compatibility."""
        return [role.value.lower() for role in cls]