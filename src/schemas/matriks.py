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

from src.models.evaluasi_enums import MatriksStatus, TindakLanjutStatus

# ===== REQUEST SCHEMAS =====

class MatriksCreate(BaseModel):
    """Schema untuk membuat matriks (auto-generated)."""
    surat_tugas_id: str = Field(..., description="ID surat tugas terkait")


class TemuanRekomendasiItem(BaseModel):
    """
    Schema untuk 1 set kondisi-kriteria-rekomendasi berserta tindak lanjut
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

    tindak_lanjut: Optional[str] = Field(
        None, 
        max_length=1000, 
        description="Tindak lanjut yang dilakukan oleh perwadag"
    )

    dokumen_pendukung_tindak_lanjut: Optional[str] = Field(
        None, 
        max_length=500, 
        description="Link dokumen pendukung tindak lanjut"
    )

    catatan_evaluator: Optional[str] = Field(
        None, 
        max_length=1000, 
        description="Catatan dari ketua tim terkait tindak lanjut"
    )

    status_tindak_lanjut: Optional[TindakLanjutStatus] = Field(
        None, 
        description="Status tindak lanjut"
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
        if len(items) > 500:
            raise ValueError("Maksimal 500 set kondisi-kriteria-rekomendasi")
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

    expected_temuan_version: Optional[int] = Field(
        None,
        description="Expected version untuk conflict detection"
    )

class MatriksStatusUpdate(BaseModel):
    """Schema untuk update status matriks."""
    status: MatriksStatus = Field(..., description="Status baru untuk matriks")

class TindakLanjutUpdate(BaseModel):
    """Schema untuk update tindak lanjut."""
    tindak_lanjut: Optional[str] = Field(None, max_length=1000, description="Narasi tindak lanjut")
    dokumen_pendukung_tindak_lanjut: Optional[str] = Field(None, max_length=500, description="Link dokumen pendukung")
    catatan_evaluator: Optional[str] = Field(None, max_length=1000, description="Catatan evaluator")

class TindakLanjutStatusUpdate(BaseModel):
    """Schema untuk update status tindak lanjut."""
    status_tindak_lanjut: TindakLanjutStatus = Field(..., description="Status tindak lanjut baru")

class UserPermissions(BaseModel):
    """Schema untuk user permissions."""
    can_edit_temuan: bool = False
    can_change_matrix_status: bool = False
    can_edit_tindak_lanjut: bool = False
    can_change_tindak_lanjut_status: bool = False
    allowed_matrix_status_changes: List[MatriksStatus] = []
    allowed_tindak_lanjut_status_changes: List[TindakLanjutStatus] = []


# ===== RESPONSE SCHEMAS =====

class MatriksResponse(BaseModel):
    """Enhanced response schema untuk matriks."""
    
    # Basic fields
    id: str
    surat_tugas_id: str
    # nomor_matriks: Optional[str] = None
    file_dokumen: Optional[str] = None
    temuan_rekomendasi_summary: Optional[TemuanRekomendasiSummary] = None
    temuan_version: int = Field(default=0, description="Version untuk conflict detection")

    
    # Enhanced file information
    file_urls: Optional[FileUrls] = None
    file_metadata: Optional[FileMetadata] = None
    
    # Status information
    is_completed: bool
    has_file: bool
    has_temuan_rekomendasi: bool = Field(default=False)
    completion_percentage: int = Field(ge=0, le=100)

    status: MatriksStatus
    is_editable: bool = Field(description="Apakah user bisa edit matriks ini")
    user_permissions: UserPermissions = Field(description="Detail permissions untuk user")
    
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


