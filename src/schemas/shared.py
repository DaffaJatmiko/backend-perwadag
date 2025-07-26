"""Shared schema components untuk sistem evaluasi."""

from typing import Optional, Dict, Any, TypeVar, Generic, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, date

T = TypeVar('T')

class BaseListResponse(BaseModel, Generic[T]):
    """Base class untuk semua list responses."""
    
    items: List[T]
    total: int
    page: int
    size: int
    pages: int
    
    @classmethod
    def create(cls, items: List[T], total: int, page: int, size: int):
        pages = (total + size - 1) // size if total > 0 else 0
        return cls(items=items, total=total, page=page, size=size, pages=pages)

class SuratTugasBasicInfo(BaseModel):
    """Basic info dari surat tugas untuk include di responses lain."""
    
    id: str
    no_surat: str
    nama_perwadag: str
    inspektorat: str
    tanggal_evaluasi_mulai: date
    tanggal_evaluasi_selesai: date
    tahun_evaluasi: int
    durasi_evaluasi: int
    evaluation_status: str
    is_evaluation_active: bool
    
    model_config = ConfigDict(from_attributes=True)


class FileMetadata(BaseModel):
    """Enhanced file metadata untuk semua file uploads."""
    
    filename: str
    original_filename: Optional[str] = None
    size: int
    size_mb: float
    content_type: str
    extension: str
    uploaded_at: datetime
    uploaded_by: Optional[str] = None
    is_viewable: bool = Field(description="Whether file can be previewed online")
    
    model_config = ConfigDict(from_attributes=True)


class FileUrls(BaseModel):
    """File URLs untuk download dan view."""
    
    file_url: str = Field(description="Direct file URL")
    download_url: str = Field(description="Download endpoint URL")
    view_url: str = Field(description="View/preview endpoint URL")
    
    model_config = ConfigDict(from_attributes=True)


class EvaluasiProgressSummary(BaseModel):
    """Summary progress evaluasi untuk dashboard."""
    
    total_stages: int = 7
    completed_stages: int
    progress_percentage: int = Field(ge=0, le=100)
    next_stage: Optional[str] = None
    last_updated: Optional[datetime] = None
    
    # Stage completion details
    surat_pemberitahuan_completed: bool = False
    entry_meeting_completed: bool = False
    konfirmasi_meeting_completed: bool = False
    exit_meeting_completed: bool = False
    matriks_completed: bool = False
    laporan_completed: bool = False
    kuisioner_completed: bool = False
    
    model_config = ConfigDict(from_attributes=True)


class PaginationInfo(BaseModel):
    """Standard pagination info untuk list responses."""
    
    page: int
    size: int
    total: int
    pages: int
    has_next: bool
    has_prev: bool
    
    @classmethod
    def create(cls, page: int, size: int, total: int) -> "PaginationInfo":
        """Create pagination info dari parameters."""
        pages = (total + size - 1) // size if total > 0 else 0
        return cls(
            page=page,
            size=size,
            total=total,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1
        )


class FilterSummary(BaseModel):
    """Summary dari applied filters untuk debugging."""
    
    applied_filters: Dict[str, Any]
    filter_count: int
    search_term: Optional[str] = None
    role_scope: str
    
    model_config = ConfigDict(from_attributes=True)


class ModuleStatistics(BaseModel):
    """Generic statistics untuk setiap module."""
    
    total_records: int
    completed_records: int
    with_files: int
    without_files: int
    completion_rate: float = Field(ge=0, le=100)
    last_updated: datetime
    
    model_config = ConfigDict(from_attributes=True)


class AuditInfo(BaseModel):
    """Audit information untuk tracking."""
    
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    last_action: Optional[str] = None
    version: int = 1
    
    model_config = ConfigDict(from_attributes=True)


class ErrorDetail(BaseModel):
    """Detailed error information."""
    
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(from_attributes=True)


class BulkOperationResult(BaseModel):
    """Result dari bulk operations."""
    
    total_requested: int
    successful: int
    failed: int
    errors: Optional[list[ErrorDetail]] = None
    success_rate: float = Field(ge=0, le=100)
    
    @classmethod
    def create(cls, total: int, successful: int, errors: list = None) -> "BulkOperationResult":
        """Create bulk operation result."""
        failed = total - successful
        success_rate = (successful / total * 100) if total > 0 else 0
        
        return cls(
            total_requested=total,
            successful=successful,
            failed=failed,
            errors=errors or [],
            success_rate=round(success_rate, 2)
        )


# =========================
# ENHANCED BASE RESPONSE SCHEMAS
# =========================

class EnhancedBaseResponse(BaseModel):
    """Enhanced base response dengan common fields."""
    
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Surat tugas relationship
    surat_tugas_id: str
    surat_tugas_info: SuratTugasBasicInfo
    
    # Quick access fields dari surat tugas
    nama_perwadag: str
    inspektorat: str
    tanggal_evaluasi_mulai: date
    tanggal_evaluasi_selesai: date
    tahun_evaluasi: int
    evaluation_status: str
    
    # File information
    has_file: bool
    is_completed: bool
    completion_percentage: int = Field(ge=0, le=100)
    
    model_config = ConfigDict(from_attributes=True)


class EnhancedListResponse(BaseModel):
    """Enhanced list response dengan additional metadata."""
    
    pagination: PaginationInfo
    filters: Optional[FilterSummary] = None
    statistics: Optional[ModuleStatistics] = None
    
    model_config = ConfigDict(from_attributes=True)


# =========================
# FILE DOWNLOAD RESPONSE SCHEMAS
# =========================

class FileDownloadInfo(BaseModel):
    """Information about downloadable file."""
    
    filename: str
    size_mb: float
    content_type: str
    download_url: str
    view_url: Optional[str] = None
    is_viewable: bool
    last_modified: datetime
    
    model_config = ConfigDict(from_attributes=True)


class MultiFileDownloadInfo(BaseModel):
    """Information for downloading multiple files."""
    
    files: list[FileDownloadInfo]
    total_files: int
    total_size_mb: float
    zip_download_url: Optional[str] = None
    estimated_zip_size_mb: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)


# =========================
# SEARCH & FILTER RESPONSE SCHEMAS
# =========================

class SearchHighlight(BaseModel):
    """Search result highlighting."""
    
    field: str
    original_text: str
    highlighted_text: str
    relevance_score: float = Field(ge=0, le=1)
    
    model_config = ConfigDict(from_attributes=True)


class SearchResult(BaseModel):
    """Individual search result."""
    
    module_type: str  # "surat_tugas", "meeting", etc.
    record_id: str
    title: str
    summary: str
    relevance_score: float = Field(ge=0, le=1)
    highlights: list[SearchHighlight] = []
    
    # Quick access info
    surat_tugas_id: str
    nama_perwadag: str
    inspektorat: str
    last_updated: datetime
    
    model_config = ConfigDict(from_attributes=True)


class CrossModuleSearchResponse(BaseModel):
    """Response untuk cross-module search."""
    
    query: str
    total_results: int
    results: list[SearchResult]
    pagination: PaginationInfo
    
    # Results by module
    results_by_module: Dict[str, int]
    search_time_ms: float
    
    model_config = ConfigDict(from_attributes=True)

class FileDeleteResponse(BaseModel):
    """Standard response untuk delete file - SEMUA entity."""
    success: bool
    message: str
    entity_id: str
    deleted_filename: str
    file_type: str = Field(description="single atau multiple")
    remaining_files: int = Field(default=0, description="0 untuk single file, N untuk multiple files")
    storage_deleted: bool = Field(default=False, description="Whether file was deleted from storage")
    database_updated: bool = Field(default=False, description="Whether database was updated")
    
    model_config = ConfigDict(from_attributes=True)