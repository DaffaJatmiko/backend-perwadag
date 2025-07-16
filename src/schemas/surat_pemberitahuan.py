# ===== src/schemas/surat_pemberitahuan.py =====
"""Schemas untuk surat pemberitahuan."""

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, date

from src.schemas.common import SuccessResponse
from src.schemas.shared import (
    SuratTugasBasicInfo, FileMetadata, FileUrls, 
    PaginationInfo, ModuleStatistics, AuditInfo, BaseListResponse
)

class SuratPemberitahuanCreate(BaseModel):
    """Schema untuk membuat surat pemberitahuan (auto-generated)."""
    surat_tugas_id: str = Field(..., description="ID surat tugas terkait")


class SuratPemberitahuanUpdate(BaseModel):
    """Schema untuk update surat pemberitahuan."""
    tanggal_surat_pemberitahuan: Optional[date] = None


class SuratPemberitahuanResponse(BaseModel):
    """Enhanced response schema untuk surat pemberitahuan."""
    
    # Basic fields
    id: str
    surat_tugas_id: str
    tanggal_surat_pemberitahuan: Optional[date] = None
    file_dokumen: Optional[str] = None
    
    # Enhanced file information
    file_urls: Optional[FileUrls] = None
    file_metadata: Optional[FileMetadata] = None
    
    # Status information
    is_completed: bool
    has_file: bool
    has_date: bool
    completion_percentage: int = Field(ge=0, le=100)
    
    # Enriched surat tugas data
    surat_tugas_info: SuratTugasBasicInfo
    nama_perwadag: str
    inspektorat: str
    tanggal_evaluasi_mulai: date
    tanggal_evaluasi_selesai: date
    tahun_evaluasi: int
    evaluation_status: str
    
    # Audit information
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class SuratPemberitahuanListResponse(BaseListResponse[SuratPemberitahuanResponse]):
    """Standardized surat pemberitahuan list response."""
    
    statistics: Optional[ModuleStatistics] = None


class SuratPemberitahuanFileUploadResponse(SuccessResponse):
    """Schema untuk response upload file."""
    surat_pemberitahuan_id: str
    file_path: str
    file_url: str
