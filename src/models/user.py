"""Simplified User model sesuai ERD - tanpa Role tables."""

from typing import Optional
from datetime import datetime, date
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import Enum as SQLEnum
import uuid as uuid_lib

from .base import BaseModel
from .enums import UserRole


class User(BaseModel, SQLModel, table=True):
    """User model yang disederhanakan sesuai ERD."""
    
    __tablename__ = "users"
    
    id: str = Field(
        default_factory=lambda: str(uuid_lib.uuid4()),
        primary_key=True,
        max_length=36
    )
    
    # Personal Information
    nama: str = Field(max_length=200, index=True, description="Nama lengkap atau nama perwadag")
    username: str = Field(max_length=50, unique=True, index=True, description="Auto-generated username")
    # tempat_lahir: str = Field(max_length=100)
    # tanggal_lahir: date
    
    # Government Position
    # pangkat: str = Field(max_length=100, description="Pangkat/golongan pegawai")
    jabatan: str = Field(max_length=200, description="Jabatan/posisi pegawai")
    
    # Authentication
    hashed_password: str = Field(description="Password yang sudah di-hash")
    email: Optional[str] = Field(default=None, unique=True, index=True, max_length=255)
    
    # Status
    is_active: bool = Field(default=True)
    last_login: Optional[datetime] = Field(default=None)
    
    # Role - ENUM FIELD (MAJOR CHANGE!)
    role: UserRole = Field(
        sa_column=Column(SQLEnum(UserRole), nullable=False, index=True),
        description="Role pengguna: admin, inspektorat, atau perwadag"
    )
    
    # Inspektorat Assignment (KHUSUS UNTUK PERWADAG)
    inspektorat: Optional[str] = Field(
        default=None, 
        max_length=100,
        description="Wajib diisi untuk role perwadag. Menentukan wilayah kerja inspektorat"
    )
    
    @property
    def display_name(self) -> str:
        """Display name adalah nama lengkap."""
        return self.nama
    
    # @property
    # def age(self) -> int:
    #     """Calculate user's age."""
    #     today = date.today()
    #     return today.year - self.tanggal_lahir.year - (
    #         (today.month, today.day) < (self.tanggal_lahir.month, self.tanggal_lahir.day)
    #     )
    
    def has_email(self) -> bool:
        """Check if user has email set."""
        return self.email is not None and self.email.strip() != ""
    
    def is_admin(self) -> bool:
        """Check if user is admin."""
        return self.role == UserRole.ADMIN
    
    def is_inspektorat(self) -> bool:
        """Check if user is inspektorat."""
        return self.role == UserRole.INSPEKTORAT
    
    def is_perwadag(self) -> bool:
        """Check if user is perwadag."""
        return self.role == UserRole.PERWADAG
    
    def get_role_display(self) -> str:
        """Get role display name."""
        role_display = {
            UserRole.ADMIN: "Administrator",
            UserRole.INSPEKTORAT: "Inspektorat",
            UserRole.PERWADAG: "Perwakilan Dagang"
        }
        return role_display.get(self.role, self.role.value)
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, nama={self.nama}, role={self.role.value})>"


class PasswordResetToken(BaseModel, SQLModel, table=True):
    """Password reset token model - tidak berubah."""
    
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