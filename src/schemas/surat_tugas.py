"""Schemas untuk surat tugas."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime, date

from src.schemas.common import SuccessResponse


# ===== REQUEST SCHEMAS =====

class SuratTugasCreate(BaseModel):
    """Schema untuk membuat surat tugas baru."""
    
    user_perwadag_id: str = Field(
        ..., 
        description="ID user perwadag yang akan dievaluasi"
    )
    tanggal_evaluasi_mulai: date = Field(
        ..., 
        description="Tanggal mulai evaluasi"
    )
    tanggal_evaluasi_selesai: date = Field(
        ..., 
        description="Tanggal selesai evaluasi"
    )
    no_surat: str = Field(
        ..., 
        min_length=1, 
        max_length=100, 
        description="Nomor surat tugas"
    )
    nama_pengedali_mutu: str = Field(
        ..., 
        min_length=1, 
        max_length=200,
        description="Nama pengedali mutu"
    )
    nama_pengendali_teknis: str = Field(
        ..., 
        min_length=1, 
        max_length=200,
        description="Nama pengendali teknis"
    )
    nama_ketua_tim: str = Field(
        ..., 
        min_length=1, 
        max_length=200,
        description="Nama ketua tim evaluasi"
    )
    
    @field_validator('tanggal_evaluasi_selesai')
    @classmethod
    def validate_tanggal_selesai(cls, tanggal_selesai: date, info) -> date:
        """Validate tanggal selesai harus setelah tanggal mulai."""
        if hasattr(info, 'data') and 'tanggal_evaluasi_mulai' in info.data:
            tanggal_mulai = info.data['tanggal_evaluasi_mulai']
            if tanggal_selesai < tanggal_mulai:
                raise ValueError("Tanggal selesai evaluasi harus setelah tanggal mulai")
        return tanggal_selesai
    
    @field_validator('no_surat')
    @classmethod
    def validate_no_surat(cls, no_surat: str) -> str:
        """Validate format nomor surat."""
        no_surat = no_surat.strip()
        if not no_surat:
            raise ValueError("Nomor surat tidak boleh kosong")
        return no_surat


class SuratTugasUpdate(BaseModel):
    """Schema untuk update surat tugas."""
    
    tanggal_evaluasi_mulai: Optional[date] = None
    tanggal_evaluasi_selesai: Optional[date] = None
    no_surat: Optional[str] = Field(None, min_length=1, max_length=100)
    nama_pengedali_mutu: Optional[str] = Field(None, min_length=1, max_length=200)
    nama_pengendali_teknis: Optional[str] = Field(None, min_length=1, max_length=200)
    nama_ketua_tim: Optional[str] = Field(None, min_length=1, max_length=200)
    
    @field_validator('no_surat')
    @classmethod
    def validate_no_surat(cls, no_surat: Optional[str]) -> Optional[str]:
        """Validate nomor surat jika diupdate."""
        if no_surat is not None:
            no_surat = no_surat.strip()
            if not no_surat:
                raise ValueError("Nomor surat tidak boleh kosong")
        return no_surat


# ===== RESPONSE SCHEMAS =====

class EvaluasiProgress(BaseModel):
    """Schema untuk tracking progress evaluasi."""
    
    surat_pemberitahuan_completed: bool = False
    entry_meeting_completed: bool = False
    konfirmasi_meeting_completed: bool = False
    exit_meeting_completed: bool = False
    matriks_completed: bool = False
    laporan_completed: bool = False
    kuisioner_completed: bool = False
    overall_percentage: int = Field(ge=0, le=100)
    
    @property
    def completed_count(self) -> int:
        """Get jumlah tahapan yang sudah completed."""
        return sum([
            self.surat_pemberitahuan_completed,
            self.entry_meeting_completed,
            self.konfirmasi_meeting_completed,
            self.exit_meeting_completed,
            self.matriks_completed,
            self.laporan_completed,
            self.kuisioner_completed
        ])
    
    @property
    def total_stages(self) -> int:
        """Get total jumlah tahapan."""
        return 7
    
    def get_next_stage(self) -> Optional[str]:
        """Get next stage yang belum completed."""
        stages = [
            ("surat_pemberitahuan", self.surat_pemberitahuan_completed),
            ("entry_meeting", self.entry_meeting_completed),
            ("konfirmasi_meeting", self.konfirmasi_meeting_completed),
            ("exit_meeting", self.exit_meeting_completed),
            ("matriks", self.matriks_completed),
            ("laporan_hasil", self.laporan_completed),
            ("kuisioner", self.kuisioner_completed)
        ]
        
        for stage_name, is_completed in stages:
            if not is_completed:
                return stage_name
        return None


class PerwardagSummary(BaseModel):
    """Schema untuk summary info perwadag."""
    
    id: str
    nama: str
    inspektorat: str
    
    model_config = ConfigDict(from_attributes=True)


class SuratTugasResponse(BaseModel):
    """Schema untuk response surat tugas."""
    
    id: str
    user_perwadag_id: str
    nama_perwadag: str
    inspektorat: str
    tanggal_evaluasi_mulai: date
    tanggal_evaluasi_selesai: date
    no_surat: str
    nama_pengedali_mutu: str
    nama_pengendali_teknis: str
    nama_ketua_tim: str
    file_surat_tugas: str
    
    # Computed fields
    tahun_evaluasi: int
    durasi_evaluasi: int
    is_evaluation_active: bool
    evaluation_status: str
    
    # Progress tracking
    progress: EvaluasiProgress
    
    # Perwadag info
    perwadag_info: PerwardagSummary
    
    # File URL
    file_surat_tugas_url: str
    
    # Audit fields
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class SuratTugasListResponse(BaseModel):
    """Schema untuk response list surat tugas dengan pagination."""
    
    surat_tugas: List[SuratTugasResponse]
    total: int
    page: int
    size: int
    pages: int


class SuratTugasCreateResponse(SuccessResponse):
    """Schema untuk response create surat tugas dengan auto-generated records."""
    
    surat_tugas: SuratTugasResponse
    auto_generated_records: Dict[str, str] = Field(
        description="IDs dari records yang auto-generated"
    )


class SuratTugasOverview(BaseModel):
    """Schema untuk overview lengkap surat tugas dengan semua related data."""
    
    surat_tugas: SuratTugasResponse
    surat_pemberitahuan: Optional[Dict[str, Any]] = None
    meetings: List[Dict[str, Any]] = []
    matriks: Optional[Dict[str, Any]] = None
    laporan_hasil: Optional[Dict[str, Any]] = None
    kuisioner: Optional[Dict[str, Any]] = None


# ===== STATISTICS SCHEMAS =====

class SuratTugasStats(BaseModel):
    """Schema untuk statistik surat tugas."""
    
    total_surat_tugas: int
    total_by_tahun: Dict[int, int]
    total_by_inspektorat: Dict[str, int]
    completed_evaluations: int
    in_progress_evaluations: int
    upcoming_evaluations: int
    completion_rate: float = Field(ge=0, le=100, description="Percentage")


# ===== BULK OPERATIONS SCHEMAS =====

class BulkDeleteRequest(BaseModel):
    """Schema untuk bulk delete surat tugas."""
    
    surat_tugas_ids: List[str] = Field(
        ..., 
        min_items=1, 
        description="List of surat tugas IDs to delete"
    )
    force_delete: bool = Field(
        default=False, 
        description="Force delete even if there are dependencies"
    )


class BulkDeleteResponse(BaseModel):
    """Schema untuk response bulk delete."""
    
    success: bool
    message: str
    deleted_count: int
    failed_count: int
    failed_ids: List[str] = []
    details: List[Dict[str, str]] = []


# ===== FILE UPLOAD SCHEMAS =====

class SuratTugasFileUploadResponse(BaseModel):
    """Schema untuk response upload file surat tugas."""
    
    success: bool
    message: str
    file_path: str
    file_url: str
    surat_tugas_id: str


class SuratTugasProgressResponse(BaseModel):
    """Schema untuk response progress tracking."""
    
    surat_tugas_id: str
    progress: EvaluasiProgress
    last_updated: datetime
    next_stage: Optional[str] = None