# ===== src/schemas/matriks.py =====
"""Enhanced schemas untuk matriks evaluasi."""

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, date

from src.schemas.common import SuccessResponse
from src.schemas.shared import (
    SuratTugasBasicInfo, FileMetadata, FileUrls, 
    PaginationInfo, ModuleStatistics
)


# ===== REQUEST SCHEMAS =====

class MatriksCreate(BaseModel):
    """Schema untuk membuat matriks (auto-generated)."""
    surat_tugas_id: str = Field(..., description="ID surat tugas terkait")


class MatriksUpdate(BaseModel):
    """Schema untuk update matriks."""
    nomor_matriks: Optional[str] = Field(None, max_length=100)


# ===== RESPONSE SCHEMAS =====

class MatriksResponse(BaseModel):
    """Enhanced response schema untuk matriks."""
    
    # Basic fields
    id: str
    surat_tugas_id: str
    nomor_matriks: Optional[str] = None
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