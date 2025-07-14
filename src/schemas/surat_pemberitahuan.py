# ===== src/schemas/surat_pemberitahuan.py =====
"""Schemas untuk surat pemberitahuan."""

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, date

from src.schemas.common import SuccessResponse


class SuratPemberitahuanCreate(BaseModel):
    """Schema untuk membuat surat pemberitahuan (auto-generated)."""
    surat_tugas_id: str = Field(..., description="ID surat tugas terkait")


class SuratPemberitahuanUpdate(BaseModel):
    """Schema untuk update surat pemberitahuan."""
    tanggal_surat_pemberitahuan: Optional[date] = None


class SuratPemberitahuanResponse(BaseModel):
    """Schema untuk response surat pemberitahuan."""
    id: str
    surat_tugas_id: str
    tanggal_surat_pemberitahuan: Optional[date] = None
    file_dokumen: Optional[str] = None
    file_dokumen_url: Optional[str] = None
    is_completed: bool
    has_file: bool
    has_date: bool
    completion_percentage: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class SuratPemberitahuanListResponse(BaseModel):
    """Schema untuk response list surat pemberitahuan."""
    surat_pemberitahuan: List[SuratPemberitahuanResponse]
    total: int
    page: int
    size: int
    pages: int


class SuratPemberitahuanFileUploadResponse(SuccessResponse):
    """Schema untuk response upload file."""
    surat_pemberitahuan_id: str
    file_path: str
    file_url: str
