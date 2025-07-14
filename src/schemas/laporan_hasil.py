# ===== src/schemas/laporan_hasil.py =====
"""Schemas untuk laporan hasil evaluasi."""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime, date

from src.schemas.common import SuccessResponse
from src.schemas.shared import (
    SuratTugasBasicInfo, FileMetadata, FileUrls, 
    PaginationInfo, ModuleStatistics, AuditInfo
)


class LaporanHasilCreate(BaseModel):
    """Schema untuk membuat laporan hasil (auto-generated)."""
    surat_tugas_id: str = Field(..., description="ID surat tugas terkait")


class LaporanHasilUpdate(BaseModel):
    """Schema untuk update laporan hasil."""
    nomor_laporan: Optional[str] = Field(None, max_length=100)
    tanggal_laporan: Optional[date] = None
    
    @field_validator('nomor_laporan')
    @classmethod
    def validate_nomor_laporan(cls, nomor_laporan: Optional[str]) -> Optional[str]:
        """Validate nomor laporan."""
        if nomor_laporan is not None:
            nomor_laporan = nomor_laporan.strip()
            if not nomor_laporan:
                raise ValueError("Nomor laporan tidak boleh kosong")
        return nomor_laporan


class LaporanHasilResponse(BaseModel):
    """Enhanced response schema untuk laporan hasil."""
    
    # Basic fields
    id: str
    surat_tugas_id: str
    nomor_laporan: Optional[str] = None
    tanggal_laporan: Optional[date] = None
    file_laporan_hasil: Optional[str] = None
    
    # Enhanced file information
    file_urls: Optional[FileUrls] = None
    file_metadata: Optional[FileMetadata] = None
    
    # Status information
    is_completed: bool
    has_file: bool
    has_nomor_laporan: bool
    has_tanggal_laporan: bool
    completion_percentage: int = Field(ge=0, le=100)
    
    # Enriched surat tugas data
    surat_tugas_info: SuratTugasBasicInfo
    nama_perwadag: str
    inspektorat: str
    tanggal_evaluasi_mulai: date
    tanggal_evaluasi_selesai: date
    tahun_evaluasi: int
    evaluation_status: str
    
    # Context information
    is_evaluation_completed: bool = Field(description="Whether evaluation period has ended")
    days_since_evaluation: Optional[int] = None
    is_overdue: bool = Field(description="Whether laporan is overdue")
    
    # Audit information
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class LaporanHasilListResponse(BaseModel):
    """Enhanced list response untuk laporan hasil."""
    
    laporan_hasil: List[LaporanHasilResponse]
    pagination: PaginationInfo
    statistics: Optional[ModuleStatistics] = None
    
    # Laporan-specific summaries
    overdue_count: int = 0
    completed_on_time_count: int = 0
    
    model_config = ConfigDict(from_attributes=True)

class LaporanHasilFileUploadResponse(SuccessResponse):
    """Schema untuk response upload file."""
    laporan_hasil_id: str
    file_path: str
    file_url: str