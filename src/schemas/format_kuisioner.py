# ===== src/schemas/format_kuisioner.py =====
"""Schemas untuk format/template kuisioner."""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime

from src.schemas.common import SuccessResponse


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
    """Schema untuk response format kuisioner."""
    id: str
    nama_template: str
    deskripsi: Optional[str] = None
    tahun: int
    link_template: str
    link_template_url: str
    display_name: str
    has_file: bool
    is_downloadable: bool
    file_extension: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class FormatKuisionerListResponse(BaseModel):
    """Schema untuk response list format kuisioner."""
    format_kuisioner: List[FormatKuisionerResponse]
    total: int
    page: int
    size: int
    pages: int


class FormatKuisionerFileUploadResponse(SuccessResponse):
    """Schema untuk response upload template."""
    format_kuisioner_id: str
    file_path: str
    file_url: str