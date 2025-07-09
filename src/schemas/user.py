"""User schemas final with clean filter schemas."""

from typing import List, Optional
from pydantic import BaseModel, EmailStr, ConfigDict, field_validator, Field
from datetime import datetime, date
import re


# Filter schemas (import from the filter module)
from src.schemas.filters import UserFilterParams, UsernameGenerationPreview, UsernameGenerationResponse


# Base schemas
class UserBase(BaseModel):
    """Base user schema with common fields."""
    full_name: str = Field(..., min_length=1, max_length=200, description="Nama lengkap tanpa gelar")
    tempat_lahir: str = Field(..., min_length=1, max_length=100)
    tanggal_lahir: date
    pangkat: str = Field(..., min_length=1, max_length=100)
    jabatan: str = Field(..., min_length=1, max_length=200)
    email: Optional[EmailStr] = Field(None, description="Email is optional")
    is_active: bool = True


# Request schemas
class UserCreate(UserBase):
    """Schema for creating a user."""
    role_names: List[str] = Field(..., min_items=1, description="List of role names to assign")
    
    @field_validator('name')
    @classmethod
    def validate_role_name(cls, name: str) -> str:
        """Validate role name format."""
        if not name.islower():
            raise ValueError("Role name must be lowercase")
        return name


class RoleUpdate(BaseModel):
    """Schema for updating a role."""
    description: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class RoleListResponse(BaseModel):
    """Schema for role list response."""
    roles: List[RoleResponse]
    total: intfield_validator('full_name')
    @classmethod
    def validate_full_name(cls, full_name: str) -> str:
        """Validate full name format."""
        full_name = full_name.strip()
        if not full_name:
            raise ValueError("Full name cannot be empty")
        
        # Allow Indonesian names with common characters, no titles
        if not re.match(r"^[a-zA-Z\s.,'-]+$", full_name):
            raise ValueError("Full name can only contain letters, spaces, and common punctuation")
        
        # Check for titles that should be removed
        titles = ['dr.', 'dr', 'prof.', 'ir.', 'drs.', 'dra.', 's.pd', 's.kom', 's.si', 's.t', 's.h', 's.e']
        words = full_name.lower().split()
        
        for word in words:
            clean_word = word.replace('.', '')
            if clean_word in titles:
                raise ValueError("Please remove titles/degrees from full name")
        
        return full_name
    
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


class UserUpdate(BaseModel):
    """Schema for updating a user."""
    full_name: Optional[str] = Field(None, min_length=1, max_length=200)
    tempat_lahir: Optional[str] = Field(None, min_length=1, max_length=100)
    tanggal_lahir: Optional[date] = None
    pangkat: Optional[str] = Field(None, min_length=1, max_length=100)
    jabatan: Optional[str] = Field(None, min_length=1, max_length=200)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    
    @field_validator('full_name')
    @classmethod
    def validate_full_name(cls, full_name: Optional[str]) -> Optional[str]:
        """Validate full name if provided."""
        if full_name is not None:
            full_name = full_name.strip()
            if not full_name:
                raise ValueError("Full name cannot be empty")
            if not re.match(r"^[a-zA-Z\s.,'-]+$", full_name):
                raise ValueError("Full name can only contain letters, spaces, and common punctuation")
        return full_name
    
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


# Response schemas
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
    first_name: str
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
    full_name: str
    username: str
    pangkat: str
    jabatan: str
    has_email: bool
    is_active: bool
    roles: List[str] = []  # Just role names
    
    model_config = ConfigDict(from_attributes=True)


# Auth schemas
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


# Common response schemas
class MessageResponse(BaseModel):
    """Standard message response."""
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str
    error_code: Optional[str] = None

# Role schemas
class RoleCreate(BaseModel):
    """Schema for creating a role."""
    name: str = Field(..., min_length=1, max_length=50, pattern="^[a-z_]+$")
    description: Optional[str] = Field(None, max_length=255)
    
    @field_validator('name')
    @classmethod
    def validate_role_name(cls, name: str) -> str:
        """Validate role name format."""
        if not name.islower():
            raise ValueError("Role name must be lowercase")
        return name


class RoleUpdate(BaseModel):
    """Schema for updating a role."""
    description: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None


class RoleListResponse(BaseModel):
    """Schema for role list response."""
    roles: List[RoleResponse]
    total: int


# Username generation response
class UsernameGenerationResponse(BaseModel):
    """Schema for username generation preview."""
    original_nama: str
    generated_username: str
    is_available: bool
    suggested_alternatives: List[str] = []