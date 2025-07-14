# ===== src/schemas/matriks.py =====
"""Schemas untuk matriks rekomendasi."""

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, date

from src.schemas.common import SuccessResponse
from src.schemas.shared import (
    SuratTugasBasicInfo, FileMetadata, FileUrls, 
    PaginationInfo, ModuleStatistics, AuditInfo
)


class MatriksCreate(BaseModel):
    """Schema untuk membuat matriks (auto-generated)."""
    surat_tugas_id: str = Field(..., description="ID surat tugas terkait")


class MatriksUpdate(BaseModel):
    """Schema untuk update matriks."""
    pass  # Only file upload, no other fields to update


class MatriksResponse(BaseModel):
    """Enhanced response schema untuk matriks."""
    
    # Basic fields
    id: str
    surat_tugas_id: str
    file_dokumen_matriks: Optional[str] = None
    
    # Enhanced file information
    file_urls: Optional[FileUrls] = None
    file_metadata: Optional[FileMetadata] = None
    
    # Status information
    is_completed: bool
    has_file: bool
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
    
    # Audit information
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)



class MatriksListResponse(BaseModel):
    """Enhanced list response untuk matriks."""
    
    matriks: List[MatriksResponse]
    pagination: PaginationInfo
    statistics: Optional[ModuleStatistics] = None
    
    model_config = ConfigDict(from_attributes=True)


class MatriksFileUploadResponse(SuccessResponse):
    """Schema untuk response upload file."""
    matriks_id: str
    file_path: str
    file_url: str