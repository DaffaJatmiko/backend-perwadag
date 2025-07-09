"""Simplified User model - nama as username."""

from typing import Optional, List
from datetime import datetime, date
from sqlmodel import Field, SQLModel, Relationship
import uuid as uuid_lib

from .base import BaseModel


class User(BaseModel, SQLModel, table=True):
    """User model for government employees (simplified)."""
    
    __tablename__ = "users"
    
    id: str = Field(
        default_factory=lambda: str(uuid_lib.uuid4()),
        primary_key=True,
        max_length=36
    )
    
    # Personal Information
    nama: str = Field(max_length=200, index=True, description="Nama lengkap (sekaligus username)")
    tempat_lahir: str = Field(max_length=100)
    tanggal_lahir: date
    
    # Government Position
    pangkat: str = Field(max_length=100)
    jabatan: str = Field(max_length=200)
    
    # Authentication
    hashed_password: str
    email: Optional[str] = Field(default=None, unique=True, index=True, max_length=255)
    
    # Status
    is_active: bool = Field(default=True)
    last_login: Optional[datetime] = Field(default=None)
    
    # Relationships
    roles: List["UserRole"] = Relationship(back_populates="user")
    
    @property
    def username(self) -> str:
        """Username is the same as nama."""
        return self.nama
    
    @property
    def display_name(self) -> str:
        """Display name is the same as nama."""
        return self.nama
    
    @property
    def age(self) -> int:
        """Calculate user's age."""
        today = date.today()
        return today.year - self.tanggal_lahir.year - (
            (today.month, today.day) < (self.tanggal_lahir.month, self.tanggal_lahir.day)
        )
    
    def has_email(self) -> bool:
        """Check if user has email set."""
        return self.email is not None and self.email.strip() != ""
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, nama={self.nama})>"


class Role(BaseModel, SQLModel, table=True):
    """Role model for RBAC."""
    
    __tablename__ = "roles"
    
    id: str = Field(
        default_factory=lambda: str(uuid_lib.uuid4()),
        primary_key=True,
        max_length=36
    )
    name: str = Field(unique=True, index=True, max_length=50)
    description: Optional[str] = Field(default=None, max_length=255)
    is_active: bool = Field(default=True)
    
    # Relationships
    users: List["UserRole"] = Relationship(back_populates="role")
    
    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name={self.name})>"


class UserRole(BaseModel, SQLModel, table=True):
    """User-Role association model."""
    
    __tablename__ = "user_roles"
    
    id: str = Field(
        default_factory=lambda: str(uuid_lib.uuid4()),
        primary_key=True,
        max_length=36
    )
    user_id: str = Field(foreign_key="users.id", index=True, max_length=36)
    role_id: str = Field(foreign_key="roles.id", index=True, max_length=36)
    
    # Optional: Add role assignment metadata
    assigned_by: Optional[str] = Field(default=None, foreign_key="users.id", max_length=36)
    assigned_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: User = Relationship(back_populates="roles")
    role: Role = Relationship(back_populates="users")
    
    def __repr__(self) -> str:
        return f"<UserRole(user_id={self.user_id}, role_id={self.role_id})>"


class PasswordResetToken(BaseModel, SQLModel, table=True):
    """Password reset token model."""
    
    __tablename__ = "password_reset_tokens"
    
    id: str = Field(
        default_factory=lambda: str(uuid_lib.uuid4()),
        primary_key=True,
        max_length=36
    )
    user_id: str = Field(foreign_key="users.id", index=True, max_length=36)
    token: str = Field(unique=True, index=True, max_length=255)
    expires_at: datetime
    used: bool = Field(default=False)
    used_at: Optional[datetime] = Field(default=None)
    
    def is_valid(self) -> bool:
        """Check if token is still valid."""
        return not self.used and datetime.utcnow() < self.expires_at
    
    def mark_as_used(self) -> None:
        """Mark token as used."""
        self.used = True
        self.used_at = datetime.utcnow()
    
    def __repr__(self) -> str:
        return f"<PasswordResetToken(user_id={self.user_id}, used={self.used})>"