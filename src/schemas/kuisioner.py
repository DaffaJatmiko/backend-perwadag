# ===== src/schemas/kuisioner.py =====
"""Enhanced schemas untuk kuisioner evaluasi."""

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, date

from src.schemas.common import SuccessResponse
from src.schemas.shared import (
    SuratTugasBasicInfo, FileMetadata, FileUrls, 
    PaginationInfo, ModuleStatistics, BaseListResponse
)


# ===== REQUEST SCHEMAS =====

class KuisionerCreate(BaseModel):
    """Schema untuk membuat kuisioner (auto-generated)."""
    surat_tugas_id: str = Field(..., description="ID surat tugas terkait")


class KuisionerUpdate(BaseModel):
    """Schema untuk update kuisioner."""
    tanggal_kuisioner: Optional[date] = Field(None, description="Tanggal pengisian kuisioner")



# ===== RESPONSE SCHEMAS =====

class KuisionerResponse(BaseModel):
    """Enhanced response schema untuk kuisioner."""
    
    # Basic fields
    id: str
    surat_tugas_id: str
    tanggal_kuisioner: Optional[date] = Field(None, description="Tanggal pengisian kuisioner")
    file_dokumen: Optional[str] = None
    
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
    
    # Audit information
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class KuisionerListResponse(BaseListResponse[KuisionerResponse]):
    """Standardized kuisioner list response."""
    
    statistics: Optional[ModuleStatistics] = None


class KuisionerFileUploadResponse(SuccessResponse):
    """Schema untuk response upload file."""
    kuisioner_id: str
    file_path: str
    file_url: str