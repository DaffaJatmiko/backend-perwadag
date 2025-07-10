"""Complete user schemas - fixed and clean."""

from typing import List, Optional
from pydantic import BaseModel, EmailStr, ConfigDict, field_validator, Field
from datetime import datetime, date
import re


# ===== BASE SCHEMAS =====

class UserBase(BaseModel):
    """Base user schema with common fields."""
    nama: str = Field(..., min_length=1, max_length=200, description="Nama lengkap tanpa gelar")
    tempat_lahir: str = Field(..., min_length=1, max_length=100)
    tanggal_lahir: date
    pangkat: str = Field(..., min_length=1, max_length=100)
    jabatan: str = Field(..., min_length=1, max_length=200)
    email: Optional[EmailStr] = Field(None, description="Email is optional")
    is_active: bool = True
    
    @field_validator('nama')
    @classmethod
    def validate_nama(cls, nama: str) -> str:
        """Validate nama format."""
        nama = nama.strip()
        if not nama:
            raise ValueError("Nama cannot be empty")
        
        # Allow Indonesian names with common characters, no titles
        if not re.match(r"^[a-zA-Z\s.,'-]+$", nama):
            raise ValueError("Nama can only contain letters, spaces, and common punctuation")
        
        # Check for titles that should be removed
        titles = ['dr.', 'dr', 'prof.', 'ir.', 'drs.', 'dra.', 's.pd', 's.kom', 's.si', 's.t', 's.h', 's.e']
        words = nama.lower().split()
        
        for word in words:
            clean_word = word.replace('.', '')
            if clean_word in titles:
                raise ValueError("Please remove titles/degrees from nama")
        
        return nama
    
    @field_validator('tempat_lahir')
    @classmethod
    def validate_tempat_lahir(cls, tempat_lahir: str) -> str:
        """Validate tempat lahir."""
        tempat_lahir = tempat_lahir.strip()
        if not tempat_lahir:
            raise ValueError("Tempat lahir cannot be empty")
        return tempat_lahir
    
    @field_validator('tanggal_lahir')
    @classmethod
    def validate_tanggal_lahir(cls, tanggal_lahir: date) -> date:
        """Validate birth date."""
        today = date.today()
        
        if tanggal_lahir > today:
            raise ValueError("Tanggal lahir cannot be in the future")
        
        # Check age range (17-70 years)
        age = today.year - tanggal_lahir.year - (
            (today.month, today.day) < (tanggal_lahir.month, tanggal_lahir.day)
        )
        
        if age < 17:
            raise ValueError("Minimum age is 17 years old")
        if age > 70:
            raise ValueError("Maximum age is 70 years old")
        
        return tanggal_lahir


# ===== REQUEST SCHEMAS =====

class UserCreate(UserBase):
    """Schema for creating a user."""
    role_names: List[str] = Field(..., min_items=1, description="List of role names to assign")


class UserUpdate(BaseModel):
    """Schema for updating a user."""
    nama: Optional[str] = Field(None, min_length=1, max_length=200)
    tempat_lahir: Optional[str] = Field(None, min_length=1, max_length=100)
    tanggal_lahir: Optional[date] = None
    pangkat: Optional[str] = Field(None, min_length=1, max_length=100)
    jabatan: Optional[str] = Field(None, min_length=1, max_length=200)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    
    @field_validator('nama')
    @classmethod
    def validate_nama(cls, nama: Optional[str]) -> Optional[str]:
        """Validate nama if provided."""
        if nama is not None:
            nama = nama.strip()
            if not nama:
                raise ValueError("Nama cannot be empty")
            if not re.match(r"^[a-zA-Z\s.,'-]+$", nama):
                raise ValueError("Nama can only contain letters, spaces, and common punctuation")
        return nama
    
    @field_validator('tanggal_lahir')
    @classmethod
    def validate_tanggal_lahir(cls, tanggal_lahir: Optional[date]) -> Optional[date]:
        """Validate birth date if provided."""
        if tanggal_lahir is not None:
            today = date.today()
            if tanggal_lahir > today:
                raise ValueError("Tanggal lahir cannot be in the future")
            
            age = today.year - tanggal_lahir.year - (
                (today.month, today.day) < (tanggal_lahir.month, tanggal_lahir.day)
            )
            
            if age < 17:
                raise ValueError("Minimum age is 17 years old")
            if age > 70:
                raise ValueError("Maximum age is 70 years old")
        
        return tanggal_lahir


class UserUpdateRole(BaseModel):
    """Schema for updating user roles."""
    role_names: List[str] = Field(..., min_items=1, description="List of role names to assign")


class UserChangePassword(BaseModel):
    """Schema for changing password."""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=128)
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, password: str) -> str:
        """Validate new password."""
        if len(password) < 6:
            raise ValueError("Password must be at least 6 characters long")
        return password


# ===== RESPONSE SCHEMAS =====

class RoleResponse(BaseModel):
    """Schema for role response."""
    id: str
    name: str
    description: Optional[str] = None
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)


class UserResponse(UserBase):
    """Schema for user response."""
    id: str
    username: str
    display_name: str
    age: int
    has_email: bool
    last_login: Optional[datetime] = None
    roles: List[RoleResponse] = []
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    """Schema for paginated user list response."""
    users: List[UserResponse]
    total: int
    page: int
    size: int
    pages: int
    
    @property
    def has_next(self) -> bool:
        """Check if there are more pages."""
        return self.page < self.pages
    
    @property
    def has_prev(self) -> bool:
        """Check if there are previous pages."""
        return self.page > 1


class UserSummary(BaseModel):
    """Schema for user summary (lighter response)."""
    id: str
    nama: str
    username: str
    pangkat: str
    jabatan: str
    has_email: bool
    is_active: bool
    roles: List[str] = []  # Just role names
    
    model_config = ConfigDict(from_attributes=True)


# ===== AUTH SCHEMAS =====

class UserLogin(BaseModel):
    """Schema for user login."""
    username: str = Field(..., description="Username for login (format: nama_depan + ddmmyyyy)")
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
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, password: str) -> str:
        """Validate new password."""
        if len(password) < 6:
            raise ValueError("Password must be at least 6 characters long")
        return password


# ===== COMMON RESPONSE SCHEMAS =====

class MessageResponse(BaseModel):
    """Standard message response."""
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str
    error_code: Optional[str] = None


# ===== ROLE SCHEMAS =====

class RoleCreate(BaseModel):
    """Schema for creating a role."""
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=255)
    
    @field_validator('name')
    @classmethod
    def validate_role_name(cls, name: str) -> str:
        """Validate role name format."""
        name = name.lower().strip()
        if not re.match(r"^[a-z_]+$", name):
            raise ValueError("Role name must be lowercase letters and underscores only")
        return name


class RoleUpdate(BaseModel):
    """Schema for updating a role."""
    description: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class RoleListResponse(BaseModel):
    """Schema for role list response."""
    roles: List[RoleResponse]
    total: int