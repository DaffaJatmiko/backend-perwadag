"""Updated filter schemas untuk simplified role system."""

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

from src.models.enums import UserRole


class UserFilterParams(BaseModel):
    """Schema for user filtering parameters - updated untuk enum role."""
    
    # Pagination
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(20, ge=1, le=100, description="Page size (max 100)")
    
    # Search
    search: Optional[str] = Field(None, description="Search by nama, username, tempat lahir, pangkat, jabatan, email, inspektorat")
    
    # Filters - UPDATED: role sekarang ENUM bukan string
    role: Optional[UserRole] = Field(None, description="Filter by role: admin, inspektorat, atau perwadag")
    inspektorat: Optional[str] = Field(None, description="Filter by inspektorat (untuk perwadag)")
    pangkat: Optional[str] = Field(None, description="Filter by pangkat")
    jabatan: Optional[str] = Field(None, description="Filter by jabatan")
    tempat_lahir: Optional[str] = Field(None, description="Filter by tempat lahir")
    
    # Status filters
    has_email: Optional[bool] = Field(None, description="Filter by email status (true=has email, false=no email)")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    
    # Age filters
    min_age: Optional[int] = Field(None, ge=17, le=70, description="Minimum age filter")
    max_age: Optional[int] = Field(None, ge=17, le=70, description="Maximum age filter")
    
    @field_validator('search')
    @classmethod
    def validate_search(cls, search: Optional[str]) -> Optional[str]:
        """Validate and clean search term."""
        if search is not None:
            search = search.strip()
            if not search:
                return None
            if len(search) > 100:
                raise ValueError("Search term too long (max 100 characters)")
        return search


class UsernameGenerationPreview(BaseModel):
    """Schema for username generation preview."""
    
    nama: str = Field(..., min_length=1, max_length=200, description="Full name atau nama perwadag")
    tanggal_lahir: str = Field(..., description="Birth date in YYYY-MM-DD format")
    role: UserRole = Field(..., description="Role untuk menentukan format username")
    
    @field_validator('nama')
    @classmethod
    def validate_nama(cls, nama: str) -> str:
        """Validate nama format."""
        nama = nama.strip()
        if not nama:
            raise ValueError("Nama cannot be empty")
        return nama


class UsernameGenerationResponse(BaseModel):
    """Schema for username generation response."""
    
    original_nama: str
    tanggal_lahir: str
    role: UserRole
    generated_username: str
    is_available: bool
    suggested_alternatives: List[str] = []
    
    class Config:
        json_schema_extra = {
            "example": {
                "original_nama": "Daffa Jatmiko",
                "tanggal_lahir": "2003-08-01",
                "role": "inspektorat",
                "generated_username": "daffa01082003",
                "is_available": True,
                "suggested_alternatives": []
            }
        }