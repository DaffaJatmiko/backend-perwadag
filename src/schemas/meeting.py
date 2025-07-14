"""Schemas untuk meetings dalam proses evaluasi."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime, date

from src.models.evaluasi_enums import MeetingType
from src.schemas.common import SuccessResponse


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
    """Schema untuk info file dalam meeting."""
    
    filename: str
    original_filename: str
    path: str
    url: str
    size: int
    uploaded_at: str
    uploaded_by: str


class MeetingResponse(BaseModel):
    """Schema untuk response meeting."""
    
    id: str
    surat_tugas_id: str
    meeting_type: MeetingType
    meeting_type_display: str
    tanggal_meeting: Optional[date] = None
    link_zoom: Optional[str] = None
    link_daftar_hadir: Optional[str] = None
    file_bukti_hadir: Optional[List[MeetingFileInfo]] = None
    
    # Status fields
    is_completed: bool
    has_files: bool
    has_zoom_link: bool
    has_daftar_hadir_link: bool
    completion_percentage: int
    total_files_uploaded: int
    
    # Audit fields
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class MeetingListResponse(BaseModel):
    """Schema untuk response list meetings dengan pagination."""
    
    meetings: List[MeetingResponse]
    total: int
    page: int
    size: int
    pages: int


class MeetingsByTypeResponse(BaseModel):
    """Schema untuk response meetings grouped by type."""
    
    entry_meeting: Optional[MeetingResponse] = None
    konfirmasi_meeting: Optional[MeetingResponse] = None
    exit_meeting: Optional[MeetingResponse] = None


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