# ===== src/schemas/kuisioner.py =====
"""Schemas untuk kuisioner."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, date

from src.schemas.common import SuccessResponse
from src.schemas.shared import (
    SuratTugasBasicInfo, FileMetadata, FileUrls, 
    PaginationInfo, ModuleStatistics, AuditInfo
)


class KuisionerCreate(BaseModel):
    """Schema untuk membuat kuisioner (auto-generated)."""
    surat_tugas_id: str = Field(..., description="ID surat tugas terkait")


class KuisionerUpdate(BaseModel):
    """Schema untuk update kuisioner."""
    pass  # Only file upload, no other fields to update


class KuisionerResponse(BaseModel):
    """Enhanced response schema untuk kuisioner."""
    
    # Basic fields
    id: str
    surat_tugas_id: str
    file_kuisioner: Optional[str] = None
    
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
    available_templates: List[Dict[str, Any]] = Field(description="Available kuisioner templates for this year")
    template_recommendations: Optional[str] = None
    
    # Audit information
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class KuisionerListResponse(BaseModel):
    """Enhanced list response untuk kuisioner."""
    
    kuisioner: List[KuisionerResponse]
    pagination: PaginationInfo
    statistics: Optional[ModuleStatistics] = None
    
    model_config = ConfigDict(from_attributes=True)


class KuisionerFileUploadResponse(SuccessResponse):
    """Schema untuk response upload file."""
    kuisioner_id: str
    file_path: str
    file_url: str