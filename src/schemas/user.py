"""Simplified user schemas tanpa Role management."""

from typing import List, Optional
from pydantic import BaseModel, EmailStr, ConfigDict, field_validator, Field
from datetime import datetime, date
import re

from src.models.enums import UserRole
from src.schemas.shared import BaseListResponse


# ===== BASE SCHEMAS =====

class UserBase(BaseModel):
    """Base user schema dengan role field."""
    nama: str = Field(..., min_length=1, max_length=200, description="Nama lengkap atau nama perwadag")
    # tempat_lahir: str = Field(..., min_length=1, max_length=100)
    # tanggal_lahir: date
    # pangkat: str = Field(..., min_length=1, max_length=100)
    jabatan: str = Field(..., min_length=1, max_length=200)
    email: Optional[EmailStr] = Field(None, description="Email is optional")
    is_active: bool = True
    role: UserRole = Field(..., description="Role pengguna: admin, inspektorat, atau perwadag")
    inspektorat: Optional[str] = Field(None, max_length=100, description="Wajib untuk role perwadag")
    
    @field_validator('nama')
    @classmethod
    def validate_nama(cls, nama: str) -> str:
        """Validate nama format."""
        nama = nama.strip()
        if not nama:
            raise ValueError("Nama cannot be empty")
        
        # For perwadag, allow special format like "ITPC Lagos – Nigeria"
        if not re.match(r"^[a-zA-Z\s.,'\-–—]+$", nama):
            raise ValueError("Nama can only contain letters, spaces, and common punctuation")
        
        return nama
    
    @field_validator('inspektorat')
    @classmethod
    def validate_inspektorat(cls, inspektorat: Optional[str], values) -> Optional[str]:
        """Validate inspektorat field based on role."""
        role = values.data.get('role') if hasattr(values, 'data') else None
        
        # For perwadag, inspektorat is required
        if role == UserRole.PERWADAG and not inspektorat:
            raise ValueError("Inspektorat is required for role 'perwadag'")
        
        # # For non-perwadag, inspektorat should be None
        # if role != UserRole.PERWADAG and inspektorat:
        #     raise ValueError("Inspektorat should only be set for role 'perwadag'")
        
        return inspektorat.strip() if inspektorat else None
    
    # @field_validator('tanggal_lahir')
    # @classmethod
    # def validate_tanggal_lahir(cls, tanggal_lahir: date) -> date:
    #     """Validate birth date."""
    #     today = date.today()
        
    #     if tanggal_lahir > today:
    #         raise ValueError("Tanggal lahir cannot be in the future")
        
    #     # Check age range (17-70 years)
    #     age = today.year - tanggal_lahir.year - (
    #         (today.month, today.day) < (tanggal_lahir.month, tanggal_lahir.day)
    #     )
        
    #     if age < 17:
    #         raise ValueError("Minimum age is 17 years old")
    #     if age > 70:
    #         raise ValueError("Maximum age is 70 years old")
        
    #     return tanggal_lahir


# ===== REQUEST SCHEMAS =====

class UserCreate(UserBase):
    """Schema for creating a user."""
    pass  # Inherits all validation from UserBase


class UserUpdate(BaseModel):
    """Schema for updating a user."""
    nama: Optional[str] = Field(None, min_length=1, max_length=200)
    # tempat_lahir: Optional[str] = Field(None, min_length=1, max_length=100)
    # tanggal_lahir: Optional[date] = None
    # pangkat: Optional[str] = Field(None, min_length=1, max_length=100)
    jabatan: Optional[str] = Field(None, min_length=1, max_length=200)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None
    inspektorat: Optional[str] = Field(None, max_length=100)
    
    @field_validator('nama')
    @classmethod
    def validate_nama(cls, nama: Optional[str]) -> Optional[str]:
        """Validate nama if provided."""
        if nama is not None:
            nama = nama.strip()
            if not nama:
                raise ValueError("Nama cannot be empty")
            if not re.match(r"^[a-zA-Z\s.,'\-–—]+$", nama):
                raise ValueError("Nama can only contain letters, spaces, and common punctuation")
        return nama


class UserChangePassword(BaseModel):
    """Schema for changing password."""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=128)


# ===== RESPONSE SCHEMAS =====

class UserResponse(UserBase):
    """Schema for user response."""
    id: str
    username: str
    display_name: str
    # age: int
    has_email: bool
    last_login: Optional[datetime] = None
    role_display: str = Field(..., description="Human-readable role name")
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    @classmethod
    def from_user_model(cls, user) -> "UserResponse":
        """Create UserResponse from User model."""
        return cls(
            id=user.id,
            nama=user.nama,
            username=user.username,
            # tempat_lahir=user.tempat_lahir,
            # tanggal_lahir=user.tanggal_lahir,
            # pangkat=user.pangkat,
            jabatan=user.jabatan,
            email=user.email,
            is_active=user.is_active,
            role=user.role,
            inspektorat=user.inspektorat,
            display_name=user.display_name,
            # age=user.age,
            has_email=user.has_email(),
            last_login=user.last_login,
            role_display=user.get_role_display(),
            created_at=user.created_at,
            updated_at=user.updated_at
        )
    
    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseListResponse[UserResponse]):
    """Standardized user list response."""
    pass


class UserSummary(BaseModel):
    """Schema for user summary (lighter response)."""
    id: str
    nama: str
    username: str
    # pangkat: str
    jabatan: str
    role: UserRole
    role_display: str
    inspektorat: Optional[str] = None
    has_email: bool
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)


# ===== AUTH SCHEMAS =====

class UserLogin(BaseModel):
    """Schema for user login."""
    username: str = Field(..., description="Username for login")
    password: str = Field(..., min_length=1)


class Token(BaseModel):
    """Schema for token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token expiry in seconds")
    user: UserResponse


class TokenRefresh(BaseModel):
    """Schema for token refresh."""
    refresh_token: str


class PasswordReset(BaseModel):
    """Schema for password reset request."""
    email: EmailStr = Field(..., description="Email must be set in profile first")


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=128)


# ===== COMMON RESPONSE SCHEMAS =====

class MessageResponse(BaseModel):
    """Standard message response."""
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str
    error_code: Optional[str] = None


class PerwadagSummary(BaseModel):
    """Schema ringkas khusus untuk daftar perwadag."""
    id: str
    nama: str = Field(..., description="Nama perwadag/perwakilan dagang")
    inspektorat: str = Field(..., description="Wilayah kerja inspektorat")
    is_active: bool = Field(..., description="Status aktif perwadag")
    
    @classmethod
    def from_user_model(cls, user) -> "PerwadagSummary":
        """Create PerwadagSummary from User model."""
        return cls(
            id=user.id,
            nama=user.nama,
            inspektorat=user.inspektorat or "",
            is_active=user.is_active
        )
    
    model_config = ConfigDict(from_attributes=True)


class PerwadagListResponse(BaseListResponse[PerwadagSummary]):
    """Standardized perwadag list response dengan pagination."""
    pass