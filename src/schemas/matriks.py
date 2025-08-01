# ===== src/schemas/matriks.py =====
"""Enhanced schemas untuk matriks evaluasi."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime, date

from src.schemas.common import SuccessResponse
from src.schemas.shared import (
    SuratTugasBasicInfo, FileMetadata, FileUrls, 
    PaginationInfo, ModuleStatistics, BaseListResponse
)


# ===== REQUEST SCHEMAS =====

class MatriksCreate(BaseModel):
    """Schema untuk membuat matriks (auto-generated)."""
    surat_tugas_id: str = Field(..., description="ID surat tugas terkait")


class TemuanRekomendasiItem(BaseModel):
    """
    Schema untuk 1 set kondisi-kriteria-rekomendasi.
    
    3-field structure untuk evaluasi:
    1. Kondisi: Situasi/keadaan yang ditemukan saat evaluasi
    2. Kriteria: Standar/aturan/ketentuan yang harus dipenuhi  
    3. Rekomendasi: Saran perbaikan untuk memenuhi kriteria
    """
    
    kondisi: str = Field(
        ..., 
        min_length=1, 
        max_length=1000, 
        description="Kondisi/situasi yang ditemukan saat evaluasi"
    )
    
    kriteria: str = Field(
        ..., 
        min_length=1, 
        max_length=1000, 
        description="Kriteria/standar/ketentuan yang harus dipenuhi"
    )
    
    rekomendasi: str = Field(
        ..., 
        min_length=1, 
        max_length=1000, 
        description="Saran perbaikan untuk memenuhi kriteria"
    )
    
    @field_validator('kondisi', 'kriteria', 'rekomendasi')
    @classmethod
    def validate_not_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Kondisi, kriteria, dan rekomendasi tidak boleh kosong")
        return value

class TemuanRekomendasiData(BaseModel):
    """Schema untuk collection kondisi-kriteria-rekomendasi."""
    
    items: List[TemuanRekomendasiItem] = Field(default_factory=list)
    
    @field_validator('items')
    @classmethod
    def validate_items(cls, items: List[TemuanRekomendasiItem]) -> List[TemuanRekomendasiItem]:
        if len(items) > 20:
            raise ValueError("Maksimal 20 set kondisi-kriteria-rekomendasi")
        return items

class TemuanRekomendasiSummary(BaseModel):
    """Schema untuk summary temuan-rekomendasi - SIMPLIFIED."""
    
    data: List[Dict[str, Any]] = Field(default_factory=list)

class MatriksUpdate(BaseModel):
    """Schema untuk update matriks."""
    temuan_rekomendasi: Optional[TemuanRekomendasiData] = Field(
        None, 
        description="Data kondisi, kriteria dan rekomendasi (REPLACE strategy)"
    )


# ===== RESPONSE SCHEMAS =====

class MatriksResponse(BaseModel):
    """Enhanced response schema untuk matriks."""
    
    # Basic fields
    id: str
    surat_tugas_id: str
    # nomor_matriks: Optional[str] = None
    file_dokumen: Optional[str] = None
    temuan_rekomendasi_summary: Optional[TemuanRekomendasiSummary] = None
    
    # Enhanced file information
    file_urls: Optional[FileUrls] = None
    file_metadata: Optional[FileMetadata] = None
    
    # Status information
    is_completed: bool
    has_file: bool
    has_temuan_rekomendasi: bool = Field(default=False)
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


class MatriksListResponse(BaseListResponse[MatriksResponse]):
    """Standardized matriks list response."""
    
    statistics: Optional[ModuleStatistics] = None


class MatriksFileUploadResponse(SuccessResponse):
    """Schema untuk response upload file."""
    matriks_id: str
    file_path: str
    file_url: str


