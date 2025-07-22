# ===== src/schemas/kuisioner.py =====
"""Enhanced schemas untuk kuisioner evaluasi."""

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator
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
class KuisionerUpdate(BaseModel):
    """Schema untuk update kuisioner."""
    tanggal_kuisioner: Optional[date] = Field(None, description="Tanggal pengisian kuisioner")
    link_dokumen_data_dukung: Optional[str] = Field(
        None, 
        max_length=1000,
        description="Link Google Drive dokumen data dukung"
    )
    
    @field_validator('link_dokumen_data_dukung')
    @classmethod
    def validate_google_drive_link(cls, link: Optional[str]) -> Optional[str]:
        """Validate Google Drive link format."""
        if link:
            link = link.strip()
            if link and not link.startswith(('http://', 'https://')):
                raise ValueError("Link harus berupa URL yang valid (dimulai dengan http:// atau https://)")
        return link



# ===== RESPONSE SCHEMAS =====

class KuisionerResponse(BaseModel):
    """Enhanced response schema untuk kuisioner."""
    
    # Basic fields
    id: str
    surat_tugas_id: str
    tanggal_kuisioner: Optional[date] = Field(None, description="Tanggal pengisian kuisioner")
    file_dokumen: Optional[str] = None
    link_dokumen_data_dukung: Optional[str] = Field(None, description="Link Google Drive dokumen data dukung")  # 🔥 FIELD BARU

    # Enhanced file information
    file_urls: Optional[FileUrls] = None
    file_metadata: Optional[FileMetadata] = None
    
    # Status information
    is_completed: bool
    has_file: bool
    has_link_dokumen: bool
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