"""Schemas untuk surat tugas."""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime, date

from src.schemas.common import SuccessResponse
from src.schemas.shared import BaseListResponse
from src.schemas.shared import FileUrls, FileMetadata
from src.schemas.user import UserSummary


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
    pengedali_mutu_id: Optional[str] = Field(None, description="ID user pengedali mutu")
    pengendali_teknis_id: Optional[str] = Field(None, description="ID user pengendali teknis")
    ketua_tim_id: Optional[str] = Field(None, description="ID user ketua tim")
    anggota_tim_ids: Optional[List[str]] = Field(None, description="List ID anggota tim")
    
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

    @field_validator('anggota_tim_ids')
    @classmethod
    def validate_anggota_tim_ids(cls, anggota_tim_ids: Optional[List[str]]) -> Optional[List[str]]:
        """Validate anggota tim IDs."""
        if anggota_tim_ids:
            # Remove duplicates and empty strings
            unique_ids = list(set([uid.strip() for uid in anggota_tim_ids if uid.strip()]))
            return unique_ids if unique_ids else None
        return None


class SuratTugasUpdate(BaseModel):
    """Schema untuk update surat tugas."""
    
    tanggal_evaluasi_mulai: Optional[date] = None
    tanggal_evaluasi_selesai: Optional[date] = None
    no_surat: Optional[str] = Field(None, min_length=1, max_length=100)
    pengedali_mutu_id: Optional[str] = None
    pengendali_teknis_id: Optional[str] = None
    ketua_tim_id: Optional[str] = None
    anggota_tim_ids: Optional[List[str]] = None
    pimpinan_inspektorat_id: Optional[str] = None
    
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

class AssignmentInfo(BaseModel):
    """Schema untuk assignment information."""
    
    pengedali_mutu: Optional[UserSummary] = None
    pengendali_teknis: Optional[UserSummary] = None
    ketua_tim: Optional[UserSummary] = None
    anggota_tim: List[UserSummary] = []
    pimpinan_inspektorat: Optional[UserSummary] = None

class SuratTugasResponse(BaseModel):
    """Schema untuk response surat tugas."""
    
    id: str
    user_perwadag_id: str
    nama_perwadag: str
    inspektorat: str
    tanggal_evaluasi_mulai: date
    tanggal_evaluasi_selesai: date
    no_surat: str
    assignment_info: AssignmentInfo
    file_surat_tugas: str

    file_urls: Optional[FileUrls] = None
    file_metadata: Optional[FileMetadata] = None
    
    # Computed fields
    tahun_evaluasi: Optional[int] = None
    durasi_evaluasi: Optional[int] = None
    is_evaluation_active: Optional[bool] = None
    evaluation_status: Optional[str] = None
    
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


class SuratTugasListResponse(BaseListResponse[SuratTugasResponse]):
    """Standardized surat tugas list response."""
    pass


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


# ===== DASHBOARD SCHEMAS =====

class CompletionStats(BaseModel):
    """Schema untuk completion statistics per relationship."""
    
    completed: int = Field(ge=0, description="Jumlah yang sudah completed")
    total: int = Field(ge=0, description="Total records")
    percentage: int = Field(ge=0, le=100, description="Persentase completion")
    remaining: int = Field(ge=0, description="Jumlah yang belum completed")


class DashboardStatistics(BaseModel):
    """Schema untuk dashboard statistics."""
    
    total_perwadag: Optional[int] = Field(None, ge=0, description="Total perwadag (only for admin/inspektorat)")
    average_progress: int = Field(ge=0, le=100, description="Average progress percentage")
    year_filter_applied: bool = Field(description="Whether year filter is applied")
    filtered_year: Optional[int] = Field(None, description="Year filter value")


class RelationshipCompletionStats(BaseModel):
    """Schema untuk completion statistics semua relationships."""
    
    surat_pemberitahuan: CompletionStats
    entry_meeting: CompletionStats
    konfirmasi_meeting: CompletionStats
    exit_meeting: CompletionStats
    matriks: CompletionStats
    laporan_hasil: CompletionStats
    kuisioner: CompletionStats


class RelationshipSummary(BaseModel):
    """Schema untuk summary relationships."""
    
    most_completed: Optional[str] = Field(None, description="Relationship with highest completion rate")
    least_completed: Optional[str] = Field(None, description="Relationship with lowest completion rate")
    total_relationships: int = Field(ge=0, description="Total number of relationships")
    fully_completed_relationships: int = Field(ge=0, description="Number of 100% completed relationships")


class RecentSuratTugasItem(SuratTugasResponse):
    """Schema untuk recent surat tugas items in dashboard."""
    
    progress_percentage: int = Field(ge=0, le=100)


class DashboardSummaryData(BaseModel):
    """Schema untuk dashboard summary data lengkap."""
    
    statistics: DashboardStatistics
    completion_stats: RelationshipCompletionStats
    recent_surat_tugas: List[RecentSuratTugasItem]
    summary_by_relationship: RelationshipSummary


class UserInfo(BaseModel):
    """Schema untuk user info in dashboard."""
    
    nama: str
    role: str
    inspektorat: Optional[str] = None


class QuickActions(BaseModel):
    """Schema untuk quick actions in dashboard."""
    
    can_create_surat_tugas: bool
    can_manage_templates: bool
    total_evaluasi: Optional[int] = Field(None, description="Total evaluasi (not shown for perwadag)")


class DashboardSummaryResponse(BaseModel):
    """Schema untuk complete dashboard summary response."""
    
    user_info: UserInfo
    year_filter: Optional[int] = None
    summary: DashboardSummaryData
    quick_actions: QuickActions