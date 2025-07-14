# ===== src/schemas/meeting.py =====
"""Enhanced schemas untuk meetings dalam proses evaluasi."""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime, date

from src.models.evaluasi_enums import MeetingType
from src.schemas.common import SuccessResponse
from src.schemas.shared import (
    SuratTugasBasicInfo, FileMetadata, FileUrls, 
    PaginationInfo, ModuleStatistics
)


# ===== REQUEST SCHEMAS =====

class MeetingCreate(BaseModel):
    """Schema untuk membuat meeting baru (auto-generated via surat tugas)."""
    
    surat_tugas_id: str = Field(..., description="ID surat tugas terkait")
    meeting_type: MeetingType = Field(..., description="Jenis meeting")


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
    uploaded_by: Optional[str] = None
    
    # Download URLs
    download_url: str
    view_url: Optional[str] = None
    is_viewable: bool
    
    model_config = ConfigDict(from_attributes=True)


class MeetingFilesInfo(BaseModel):
    """Enhanced file information untuk multiple files."""
    
    files: List[MeetingFileInfo]
    total_files: int
    total_size: int
    total_size_mb: float
    
    # Bulk download URLs
    download_all_url: str = Field(description="Download all files as ZIP")
    
    model_config = ConfigDict(from_attributes=True)


class UploadedFileInfo(BaseModel):
    """Schema untuk file yang berhasil diupload."""
    
    filename: str = Field(..., description="Generated filename")
    original_filename: str = Field(..., description="Original filename")
    path: str = Field(..., description="File path")
    size: int = Field(..., description="File size in bytes")
    size_mb: float = Field(..., description="File size in MB")
    content_type: str = Field(..., description="MIME type")
    uploaded_at: str = Field(..., description="Upload timestamp")
    uploaded_by: str = Field(..., description="User who uploaded")


class MeetingResponse(BaseModel):
    """Enhanced response schema untuk meetings."""
    
    # Basic fields
    id: str
    surat_tugas_id: str
    meeting_type: MeetingType
    tanggal_meeting: Optional[date] = None
    link_zoom: Optional[str] = None
    link_daftar_hadir: Optional[str] = None
    
    # Files information - ADD THIS FIELD
    files_info: Optional[MeetingFilesInfo] = None
    
    # Status information (simplified)
    is_completed: bool
    has_files: bool = Field(default=False, description="Whether meeting has files")
    has_date: bool
    has_links: bool
    completion_percentage: int = Field(ge=0, le=100)
    
    # Meeting type display
    meeting_type_display: str
    meeting_order: int = Field(description="Order dalam workflow evaluasi")
    
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


class MeetingListResponse(BaseModel):
    """Simplified list response untuk meetings."""
    
    meetings: List[MeetingResponse]
    pagination: PaginationInfo
    statistics: Optional[ModuleStatistics] = None
    
    # Meeting type summary (simplified)
    meeting_type_summary: Optional[Dict[str, int]] = Field(
        None, description="Count per meeting type"
    )
    
    model_config = ConfigDict(from_attributes=True)


class MeetingFileUploadResponse(SuccessResponse):
    """Schema untuk response upload files - FIXED."""
    meeting_id: str
    uploaded_files: List[UploadedFileInfo]  # Use proper schema instead of Dict[str, str]
    total_files: int
    total_size_mb: float


class MeetingFileDeleteResponse(SuccessResponse):
    """Schema untuk response delete file."""
    meeting_id: str
    deleted_file: str
    remaining_files: int