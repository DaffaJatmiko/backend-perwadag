# ===== src/schemas/format_kuisioner.py =====
"""Schemas untuk format/template kuisioner."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime

from src.schemas.common import SuccessResponse
from src.schemas.shared import (
    SuratTugasBasicInfo, FileMetadata, FileUrls, 
    PaginationInfo, ModuleStatistics, AuditInfo, BaseListResponse
)


class FormatKuisionerCreate(BaseModel):
    """Schema untuk membuat format kuisioner."""
    nama_template: str = Field(..., min_length=1, max_length=200)
    deskripsi: Optional[str] = None
    tahun: int = Field(..., ge=2020, le=2030)
    
    @field_validator('nama_template')
    @classmethod
    def validate_nama_template(cls, nama_template: str) -> str:
        """Validate nama template."""
        nama_template = nama_template.strip()
        if not nama_template:
            raise ValueError("Nama template tidak boleh kosong")
        return nama_template


class FormatKuisionerUpdate(BaseModel):
    """Schema untuk update format kuisioner."""
    nama_template: Optional[str] = Field(None, min_length=1, max_length=200)
    deskripsi: Optional[str] = None
    tahun: Optional[int] = Field(None, ge=2020, le=2030)
    
    @field_validator('nama_template')
    @classmethod
    def validate_nama_template(cls, nama_template: Optional[str]) -> Optional[str]:
        """Validate nama template."""
        if nama_template is not None:
            nama_template = nama_template.strip()
            if not nama_template:
                raise ValueError("Nama template tidak boleh kosong")
        return nama_template


class FormatKuisionerResponse(BaseModel):
    """Enhanced response schema untuk format kuisioner."""
    
    # Basic fields
    id: str
    nama_template: str
    deskripsi: Optional[str] = None
    tahun: int
    link_template: str
    
    # Enhanced file information
    file_urls: Optional[FileUrls] = None
    file_metadata: Optional[FileMetadata] = None
    
    # Computed fields
    display_name: str
    has_file: bool
    is_downloadable: bool
    is_current_year: bool = Field(description="Whether template is for current year")
    
    # Usage statistics
    usage_count: int = Field(description="How many times template has been downloaded")
    last_used: Optional[datetime] = None
    
    # Audit information
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class FormatKuisionerListResponse(BaseListResponse[FormatKuisionerResponse]):
    """Standardized format kuisioner list response."""
    
    statistics: Optional[ModuleStatistics] = None
    # by_year_summary: Optional[Dict[int, int]] = None


class FormatKuisionerFileUploadResponse(SuccessResponse):
    """Schema untuk response upload template."""
    format_kuisioner_id: str
    file_path: str
    file_url: str