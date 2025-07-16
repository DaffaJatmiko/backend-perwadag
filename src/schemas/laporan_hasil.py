# ===== src/schemas/laporan_hasil.py =====
"""Enhanced schemas untuk laporan hasil evaluasi."""

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, date

from src.schemas.common import SuccessResponse
from src.schemas.shared import (
    SuratTugasBasicInfo, FileMetadata, FileUrls, 
    PaginationInfo, ModuleStatistics, BaseListResponse
)


# ===== REQUEST SCHEMAS =====

class LaporanHasilCreate(BaseModel):
    """Schema untuk membuat laporan hasil (auto-generated)."""
    surat_tugas_id: str = Field(..., description="ID surat tugas terkait")


class LaporanHasilUpdate(BaseModel):
    """Schema untuk update laporan hasil."""
    nomor_laporan: Optional[str] = Field(None, max_length=100)
    tanggal_laporan: Optional[date] = Field(None, description="Tanggal laporan hasil evaluasi")


# ===== RESPONSE SCHEMAS =====

class LaporanHasilResponse(BaseModel):
    """Enhanced response schema untuk laporan hasil."""
    
    # Basic fields
    id: str
    surat_tugas_id: str
    nomor_laporan: Optional[str] = None
    tanggal_laporan: Optional[date] = None
    file_dokumen: Optional[str] = None
    
    # Enhanced file information
    file_urls: Optional[FileUrls] = None
    file_metadata: Optional[FileMetadata] = None
    
    # Status information
    is_completed: bool
    has_file: bool
    has_nomor: bool
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


class LaporanHasilListResponse(BaseListResponse[LaporanHasilResponse]):
    """Standardized laporan hasil list response."""
    
    statistics: Optional[ModuleStatistics] = None


class LaporanHasilFileUploadResponse(SuccessResponse):
    """Schema untuk response upload file."""
    laporan_hasil_id: str
    file_path: str
    file_url: str