"""Schemas untuk meetings dalam proses evaluasi."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime, date

from src.models.evaluasi_enums import MeetingType
from src.schemas.common import SuccessResponse
from src.schemas.shared import (
    SuratTugasBasicInfo, FileMetadata, FileUrls, 
    PaginationInfo, ModuleStatistics, AuditInfo
)


# ===== REQUEST SCHEMAS =====

class MeetingCreate(BaseModel):
    """Schema untuk membuat meeting baru (auto-generated via surat tugas)."""
    
    surat_tugas_id: str = Field(..., description="ID surat tugas terkait")
    meeting_type: MeetingType = Field(..., description="Jenis meeting")
    
    # Note: Other fields akan di-set via update, bukan create


class MeetingUpdate(BaseModel):
    """Schema untuk update meeting."""
    
    tanggal_meeting: Optional[date] = None
    link_zoom: Optional[str] = Field(None, max_length=500)
    link_daftar_hadir: Optional[str] = Field(None, max_length=500)
    
    @field_validator('link_zoom')
    @classmethod
    def validate_zoom_link(cls, link_zoom: Optional[str]) -> Optional[str]:
        """Validate zoom link format."""
        if link_zoom is not None:
            link_zoom = link_zoom.strip()
            if link_zoom and not link_zoom.startswith(('http://', 'https://')):
                raise ValueError("Zoom link must be a valid URL")
        return link_zoom
    
    @field_validator('link_daftar_hadir')
    @classmethod
    def validate_daftar_hadir_link(cls, link_daftar_hadir: Optional[str]) -> Optional[str]:
        """Validate daftar hadir link format."""
        if link_daftar_hadir is not None:
            link_daftar_hadir = link_daftar_hadir.strip()
            if link_daftar_hadir and not link_daftar_hadir.startswith(('http://', 'https://')):
                raise ValueError("Daftar hadir link must be a valid URL")
        return link_daftar_hadir


class MeetingFileUploadRequest(BaseModel):
    """Schema untuk upload multiple files ke meeting."""
    
    # Files akan di-handle via UploadFile di endpoint
    replace_existing: bool = Field(
        default=False, 
        description="Replace existing files or add to existing"
    )


# ===== RESPONSE SCHEMAS =====

class MeetingFileInfo(BaseModel):
    """Enhanced file info untuk meeting files."""
    
    filename: str
    original_filename: str
    path: str
    size: int
    size_mb: float
    content_type: str
    uploaded_at: datetime
    uploaded_by: str
    
    # Download URLs
    download_url: str
    view_url: Optional[str] = None
    is_viewable: bool
    
    model_config = ConfigDict(from_attributes=True)


class MeetingResponse(BaseModel):
    """Enhanced response schema untuk meetings."""
    
    # Basic fields
    id: str
    surat_tugas_id: str
    meeting_type: MeetingType
    meeting_type_display: str
    tanggal_meeting: Optional[date] = None
    link_zoom: Optional[str] = None
    link_daftar_hadir: Optional[str] = None
    
    # Enhanced file information
    file_bukti_hadir: Optional[List[MeetingFileInfo]] = None
    total_files_uploaded: int = 0
    total_files_size_mb: float = 0.0
    
    # Status information
    is_completed: bool
    has_files: bool
    has_zoom_link: bool
    has_daftar_hadir_link: bool
    completion_percentage: int = Field(ge=0, le=100)
    
    # Enriched surat tugas data
    surat_tugas_info: SuratTugasBasicInfo
    nama_perwadag: str
    inspektorat: str
    tanggal_evaluasi_mulai: date
    tanggal_evaluasi_selesai: date
    tahun_evaluasi: int
    evaluation_status: str
    
    # Additional meeting context
    days_until_evaluation: Optional[int] = None
    is_evaluation_period: bool = False
    meeting_order: int = Field(description="Order in evaluation process (1-3)")
    
    # Audit information
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class MeetingListResponse(BaseModel):
    """Enhanced list response untuk meetings."""
    
    meetings: List[MeetingResponse]
    pagination: PaginationInfo
    statistics: Optional[ModuleStatistics] = None
    
    # Meeting-specific summaries
    by_type_summary: Dict[str, int] = Field(description="Count by meeting type")
    by_status_summary: Dict[str, int] = Field(description="Count by completion status")
    
    model_config = ConfigDict(from_attributes=True)


class MeetingsByTypeResponse(BaseModel):
    """Enhanced response untuk meetings grouped by type."""
    
    entry_meeting: Optional[MeetingResponse] = None
    konfirmasi_meeting: Optional[MeetingResponse] = None
    exit_meeting: Optional[MeetingResponse] = None
    
    # Summary information
    total_meetings: int = 3
    completed_meetings: int = 0
    progress_percentage: int = Field(ge=0, le=100)
    next_meeting_type: Optional[str] = None
    
    # Surat tugas context
    surat_tugas_info: SuratTugasBasicInfo
    
    model_config = ConfigDict(from_attributes=True)


class MeetingFileUploadResponse(SuccessResponse):
    """Schema untuk response upload files ke meeting."""
    
    meeting_id: str
    uploaded_files: List[MeetingFileInfo]
    total_uploaded: int
    total_files_now: int


class MeetingFileDeleteResponse(BaseModel):
    """Schema untuk response hapus file dari meeting."""
    
    success: bool
    message: str
    deleted_filename: str
    remaining_files: int


# ===== STATISTICS SCHEMAS =====

class MeetingStats(BaseModel):
    """Schema untuk statistik meetings."""
    
    total_meetings: int
    completed_meetings: int
    meetings_with_files: int
    meetings_with_zoom: int
    meetings_by_type: Dict[str, int]
    completion_rate: float = Field(ge=0, le=100)


class MeetingProgress(BaseModel):
    """Schema untuk progress tracking meetings."""
    
    surat_tugas_id: str
    entry_meeting_progress: int
    konfirmasi_meeting_progress: int
    exit_meeting_progress: int
    overall_meetings_progress: int
    completed_meetings_count: int
    total_meetings_count: int = 3  # Always 3 meetings per surat tugas


# ===== BULK OPERATIONS SCHEMAS =====

class BulkMeetingUpdate(BaseModel):
    """Schema untuk bulk update meetings."""
    
    meeting_ids: List[str] = Field(..., min_items=1)
    update_data: MeetingUpdate


class BulkMeetingUpdateResponse(BaseModel):
    """Schema untuk response bulk update meetings."""
    
    success: bool
    message: str
    updated_count: int
    failed_count: int
    failed_ids: List[str] = []


# ===== VALIDATION SCHEMAS =====

class MeetingValidation(BaseModel):
    """Schema untuk validasi meeting data."""
    
    has_required_fields: bool
    missing_fields: List[str] = []
    has_valid_links: bool
    invalid_links: List[str] = []
    file_count: int
    is_ready_for_completion: bool
    validation_messages: List[str] = []