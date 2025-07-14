"""Updated filter schemas untuk sistem evaluasi dan existing filters."""

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from datetime import date

from src.models.enums import UserRole
from src.models.evaluasi_enums import MeetingType


# ===== EXISTING USER FILTERS (UNCHANGED) =====

class UserFilterParams(BaseModel):
    """Schema for user filtering parameters - updated untuk enum role."""
    
    # Pagination
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(20, ge=1, le=100, description="Page size (max 100)")
    
    # Search
    search: Optional[str] = Field(None, description="Search by nama, username, tempat lahir, pangkat, jabatan, email, inspektorat")
    
    # Filters - UPDATED: role sekarang ENUM bukan string
    role: Optional[UserRole] = Field(None, description="Filter by role: admin, inspektorat, atau perwadag")
    inspektorat: Optional[str] = Field(None, description="Filter by inspektorat (untuk perwadag)")
    pangkat: Optional[str] = Field(None, description="Filter by pangkat")
    jabatan: Optional[str] = Field(None, description="Filter by jabatan")
    tempat_lahir: Optional[str] = Field(None, description="Filter by tempat lahir")
    
    # Status filters
    has_email: Optional[bool] = Field(None, description="Filter by email status (true=has email, false=no email)")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    
    # Age filters
    min_age: Optional[int] = Field(None, ge=17, le=70, description="Minimum age filter")
    max_age: Optional[int] = Field(None, ge=17, le=70, description="Maximum age filter")
    
    @field_validator('search')
    @classmethod
    def validate_search(cls, search: Optional[str]) -> Optional[str]:
        """Validate and clean search term."""
        if search is not None:
            search = search.strip()
            if not search:
                return None
            if len(search) > 100:
                raise ValueError("Search term too long (max 100 characters)")
        return search


class UsernameGenerationPreview(BaseModel):
    """Schema for username generation preview."""
    
    nama: str = Field(..., min_length=1, max_length=200, description="Full name atau nama perwadag")
    tanggal_lahir: str = Field(..., description="Birth date in YYYY-MM-DD format")
    role: UserRole = Field(..., description="Role untuk menentukan format username")
    
    @field_validator('nama')
    @classmethod
    def validate_nama(cls, nama: str) -> str:
        """Validate nama format."""
        nama = nama.strip()
        if not nama:
            raise ValueError("Nama cannot be empty")
        return nama


class UsernameGenerationResponse(BaseModel):
    """Schema for username generation response."""
    
    original_nama: str
    tanggal_lahir: str
    role: UserRole
    generated_username: str
    is_available: bool
    suggested_alternatives: List[str] = []
    
    class Config:
        json_schema_extra = {
            "example": {
                "original_nama": "Daffa Jatmiko",
                "tanggal_lahir": "2003-08-01",
                "role": "inspektorat",
                "generated_username": "daffa01082003",
                "is_available": True,
                "suggested_alternatives": []
            }
        }


# ===== NEW EVALUASI FILTERS =====

class SuratTugasFilterParams(BaseModel):
    """Filter parameters untuk surat tugas."""
    
    # Pagination
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(20, ge=1, le=100, description="Page size (max 100)")
    
    # Search
    search: Optional[str] = Field(
        None, 
        description="Search by nama_perwadag, no_surat, nama tim"
    )
    
    # Basic filters
    inspektorat: Optional[str] = Field(
        None, 
        description="Filter by inspektorat"
    )
    user_perwadag_id: Optional[str] = Field(
        None, 
        description="Filter by specific perwadag"
    )
    
    # Date filters
    tahun_evaluasi: Optional[int] = Field(
        None, 
        ge=2020, 
        le=2030, 
        description="Filter by tahun evaluasi"
    )
    tanggal_mulai_from: Optional[date] = Field(
        None, 
        description="Filter evaluasi mulai dari tanggal"
    )
    tanggal_mulai_to: Optional[date] = Field(
        None, 
        description="Filter evaluasi mulai sampai tanggal"
    )
    
    # Status filters
    is_active: Optional[bool] = Field(
        None, 
        description="Filter by active evaluation status"
    )
    has_file: Optional[bool] = Field(
        None, 
        description="Filter by file upload status"
    )
    
    # Progress filters
    is_completed: Optional[bool] = Field(
        None, 
        description="Filter by completion status"
    )
    min_progress: Optional[int] = Field(
        None, 
        ge=0, 
        le=100, 
        description="Minimum progress percentage"
    )
    
    @field_validator('search')
    @classmethod
    def validate_search(cls, search: Optional[str]) -> Optional[str]:
        """Validate and clean search term."""
        if search is not None:
            search = search.strip()
            if not search:
                return None
            if len(search) > 100:
                raise ValueError("Search term too long (max 100 characters)")
        return search
    
    @field_validator('tanggal_mulai_to')
    @classmethod
    def validate_date_range(cls, tanggal_to: Optional[date], info) -> Optional[date]:
        """Validate date range."""
        if tanggal_to and hasattr(info, 'data') and 'tanggal_mulai_from' in info.data:
            tanggal_from = info.data['tanggal_mulai_from']
            if tanggal_from and tanggal_to < tanggal_from:
                raise ValueError("End date must be after start date")
        return tanggal_to


class MeetingFilterParams(BaseModel):
    """Filter parameters untuk meetings."""
    
    # Pagination
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(20, ge=1, le=100, description="Page size (max 100)")
    
    # Search
    search: Optional[str] = Field(
        None, 
        description="Search by meeting info"
    )
    
    # Basic filters
    surat_tugas_id: Optional[str] = Field(
        None, 
        description="Filter by surat tugas"
    )
    meeting_type: Optional[MeetingType] = Field(
        None, 
        description="Filter by meeting type"
    )
    inspektorat: Optional[str] = Field(
        None, 
        description="Filter by inspektorat"
    )
    
    # Date filters
    tanggal_from: Optional[date] = Field(
        None, 
        description="Filter meeting dari tanggal"
    )
    tanggal_to: Optional[date] = Field(
        None, 
        description="Filter meeting sampai tanggal"
    )
    tahun: Optional[int] = Field(
        None, 
        ge=2020, 
        le=2030, 
        description="Filter by tahun meeting"
    )
    
    # Status filters
    has_tanggal: Optional[bool] = Field(
        None, 
        description="Filter by tanggal meeting status"
    )
    has_files: Optional[bool] = Field(
        None, 
        description="Filter by file upload status"
    )
    has_zoom_link: Optional[bool] = Field(
        None, 
        description="Filter by zoom link status"
    )
    
    @field_validator('search')
    @classmethod
    def validate_search(cls, search: Optional[str]) -> Optional[str]:
        """Validate search term."""
        if search is not None:
            search = search.strip()
            if not search:
                return None
            if len(search) > 100:
                raise ValueError("Search term too long")
        return search


class SuratPemberitahuanFilterParams(BaseModel):
    """Filter parameters untuk surat pemberitahuan - TAMBAHKAN ini."""
    
    # Pagination
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(20, ge=1, le=100, description="Page size (max 100)")
    
    # Search
    search: Optional[str] = Field(None, description="Search by nama perwadag, no surat, inspektorat")
    
    # Surat tugas related filters
    inspektorat: Optional[str] = Field(None, description="Filter by inspektorat")
    user_perwadag_id: Optional[str] = Field(None, description="Filter by specific perwadag")
    tahun_evaluasi: Optional[int] = Field(None, ge=2020, le=2030, description="Filter by tahun evaluasi")
    
    # Specific filters
    surat_tugas_id: Optional[str] = Field(None, description="Filter by surat tugas")
    has_file: Optional[bool] = Field(None, description="Filter by file upload status")
    has_date: Optional[bool] = Field(None, description="Filter by tanggal status")
    is_completed: Optional[bool] = Field(None, description="Filter by completion status")
    
    # Date range filters
    tanggal_from: Optional[date] = Field(None, description="Filter from tanggal surat")
    tanggal_to: Optional[date] = Field(None, description="Filter to tanggal surat")
    created_from: Optional[date] = Field(None, description="Filter created from date")
    created_to: Optional[date] = Field(None, description="Filter created to date")
    
    @field_validator('search')
    @classmethod
    def validate_search(cls, search: Optional[str]) -> Optional[str]:
        """Validate and clean search term."""
        if search is not None:
            search = search.strip()
            if not search:
                return None
            if len(search) > 100:
                raise ValueError("Search term too long (max 100 characters)")
        return search


class MeetingFilterParams(BaseModel):
    """Filter parameters untuk meetings - TAMBAHKAN ini."""
    
    # Pagination
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(20, ge=1, le=100, description="Page size (max 100)")
    
    # Search
    search: Optional[str] = Field(None, description="Search by meeting info, nama perwadag")
    
    # Basic filters
    surat_tugas_id: Optional[str] = Field(None, description="Filter by surat tugas")
    meeting_type: Optional[MeetingType] = Field(None, description="Filter by meeting type")
    meeting_types: Optional[List[MeetingType]] = Field(None, description="Filter by multiple meeting types")
    
    # Surat tugas related filters
    inspektorat: Optional[str] = Field(None, description="Filter by inspektorat")
    user_perwadag_id: Optional[str] = Field(None, description="Filter by specific perwadag")
    tahun_evaluasi: Optional[int] = Field(None, ge=2020, le=2030, description="Filter by tahun evaluasi")
    
    # Meeting status filters
    has_tanggal: Optional[bool] = Field(None, description="Filter by tanggal meeting status")
    has_zoom_link: Optional[bool] = Field(None, description="Filter by zoom link status")
    has_daftar_hadir_link: Optional[bool] = Field(None, description="Filter by daftar hadir link status")
    has_files: Optional[bool] = Field(None, description="Filter by file upload status")
    
    # File filters
    file_count_min: Optional[int] = Field(None, ge=0, description="Minimum file count")
    file_count_max: Optional[int] = Field(None, ge=0, description="Maximum file count")
    
    # Date filters
    tanggal_meeting_from: Optional[date] = Field(None, description="Filter from tanggal meeting")
    tanggal_meeting_to: Optional[date] = Field(None, description="Filter to tanggal meeting")
    created_from: Optional[date] = Field(None, description="Filter created from date")
    created_to: Optional[date] = Field(None, description="Filter created to date")
    
    @field_validator('search')
    @classmethod
    def validate_search(cls, search: Optional[str]) -> Optional[str]:
        """Validate search term."""
        if search is not None:
            search = search.strip()
            if not search:
                return None
            if len(search) > 100:
                raise ValueError("Search term too long")
        return search


class MatriksFilterParams(BaseModel):
    """Filter parameters untuk matriks - TAMBAHKAN ini."""
    
    # Pagination
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(20, ge=1, le=100, description="Page size (max 100)")
    
    # Search
    search: Optional[str] = Field(None, description="Search by nama perwadag, inspektorat")
    
    # Surat tugas related filters
    inspektorat: Optional[str] = Field(None, description="Filter by inspektorat")
    user_perwadag_id: Optional[str] = Field(None, description="Filter by specific perwadag")
    tahun_evaluasi: Optional[int] = Field(None, ge=2020, le=2030, description="Filter by tahun evaluasi")
    
    # Specific filters
    surat_tugas_id: Optional[str] = Field(None, description="Filter by surat tugas")
    has_file: Optional[bool] = Field(None, description="Filter by file upload status")
    is_completed: Optional[bool] = Field(None, description="Filter by completion status")
    
    # Date filters
    created_from: Optional[date] = Field(None, description="Filter created from date")
    created_to: Optional[date] = Field(None, description="Filter created to date")
    
    @field_validator('search')
    @classmethod
    def validate_search(cls, search: Optional[str]) -> Optional[str]:
        """Validate search term."""
        if search is not None:
            search = search.strip()
            if not search:
                return None
            if len(search) > 100:
                raise ValueError("Search term too long")
        return search


class LaporanHasilFilterParams(BaseModel):
    """Filter parameters untuk laporan hasil - TAMBAHKAN ini."""
    
    # Pagination
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(20, ge=1, le=100, description="Page size (max 100)")
    
    # Search
    search: Optional[str] = Field(None, description="Search by nomor laporan, nama perwadag")
    
    # Surat tugas related filters
    inspektorat: Optional[str] = Field(None, description="Filter by inspektorat")
    user_perwadag_id: Optional[str] = Field(None, description="Filter by specific perwadag")
    tahun_evaluasi: Optional[int] = Field(None, ge=2020, le=2030, description="Filter by tahun evaluasi")
    
    # Specific filters
    surat_tugas_id: Optional[str] = Field(None, description="Filter by surat tugas")
    nomor_laporan: Optional[str] = Field(None, description="Filter by nomor laporan")
    has_file: Optional[bool] = Field(None, description="Filter by file upload status")
    has_nomor: Optional[bool] = Field(None, description="Filter by nomor laporan status")
    has_tanggal: Optional[bool] = Field(None, description="Filter by tanggal laporan status")
    is_completed: Optional[bool] = Field(None, description="Filter by completion status")
    
    # Date filters specific to laporan
    tanggal_laporan_from: Optional[date] = Field(None, description="Filter from tanggal laporan")
    tanggal_laporan_to: Optional[date] = Field(None, description="Filter to tanggal laporan")
    created_from: Optional[date] = Field(None, description="Filter created from date")
    created_to: Optional[date] = Field(None, description="Filter created to date")
    
    @field_validator('search')
    @classmethod
    def validate_search(cls, search: Optional[str]) -> Optional[str]:
        """Validate search term."""
        if search is not None:
            search = search.strip()
            if not search:
                return None
            if len(search) > 100:
                raise ValueError("Search term too long")
        return search


class KuisionerFilterParams(BaseModel):
    """Filter parameters untuk kuisioner - TAMBAHKAN ini."""
    
    # Pagination
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(20, ge=1, le=100, description="Page size (max 100)")
    
    # Search
    search: Optional[str] = Field(None, description="Search by nama perwadag, inspektorat")
    
    # Surat tugas related filters
    inspektorat: Optional[str] = Field(None, description="Filter by inspektorat")
    user_perwadag_id: Optional[str] = Field(None, description="Filter by specific perwadag")
    tahun_evaluasi: Optional[int] = Field(None, ge=2020, le=2030, description="Filter by tahun evaluasi")
    
    # Specific filters
    surat_tugas_id: Optional[str] = Field(None, description="Filter by surat tugas")
    has_file: Optional[bool] = Field(None, description="Filter by file upload status")
    is_completed: Optional[bool] = Field(None, description="Filter by completion status")
    
    # Date filters
    created_from: Optional[date] = Field(None, description="Filter created from date")
    created_to: Optional[date] = Field(None, description="Filter created to date")
    
    @field_validator('search')
    @classmethod
    def validate_search(cls, search: Optional[str]) -> Optional[str]:
        """Validate search term."""
        if search is not None:
            search = search.strip()
            if not search:
                return None
            if len(search) > 100:
                raise ValueError("Search term too long")
        return search

class FormatKuisionerFilterParams(BaseModel):
    """Filter parameters untuk format kuisioner."""
    
    # Pagination
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(20, ge=1, le=100, description="Page size (max 100)")
    
    # Search
    search: Optional[str] = Field(
        None, 
        description="Search by nama template, deskripsi"
    )
    
    # Filters
    tahun: Optional[int] = Field(
        None, 
        ge=2020, 
        le=2030, 
        description="Filter by tahun template"
    )
    has_file: Optional[bool] = Field(
        None, 
        description="Filter by file availability"
    )
    
    @field_validator('search')
    @classmethod
    def validate_search(cls, search: Optional[str]) -> Optional[str]:
        """Validate search term."""
        if search is not None:
            search = search.strip()
            if not search:
                return None
            if len(search) > 100:
                raise ValueError("Search term too long")
        return search


class EvaluasiDashboardFilter(BaseModel):
    """Filter untuk dashboard evaluasi."""
    
    # Time range
    tahun: Optional[int] = Field(
        None, 
        ge=2020, 
        le=2030, 
        description="Filter by specific year"
    )
    bulan: Optional[int] = Field(
        None, 
        ge=1, 
        le=12, 
        description="Filter by specific month"
    )
    
    # Scope
    inspektorat: Optional[str] = Field(
        None, 
        description="Filter by inspektorat"
    )
    user_perwadag_id: Optional[str] = Field(
        None, 
        description="Filter by specific perwadag"
    )
    
    # Status
    status: Optional[str] = Field(
        None, 
        description="Filter by evaluation status"
    )


class FileUploadFilter(BaseModel):
    """Filter untuk file uploads dalam evaluasi."""
    
    # Pagination
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(20, ge=1, le=100, description="Page size")
    
    # Filters
    file_type: Optional[str] = Field(
        None, 
        description="Filter by file type"
    )
    surat_tugas_id: Optional[str] = Field(
        None, 
        description="Filter by surat tugas"
    )
    inspektorat: Optional[str] = Field(
        None, 
        description="Filter by inspektorat"
    )
    uploaded_by: Optional[str] = Field(
        None, 
        description="Filter by uploader"
    )
    
    # Date range
    uploaded_from: Optional[date] = Field(
        None, 
        description="Filter uploads from date"
    )
    uploaded_to: Optional[date] = Field(
        None, 
        description="Filter uploads to date"
    )
    
    # File status
    has_file: Optional[bool] = Field(
        None, 
        description="Filter by file existence"
    )


# ===== COMPREHENSIVE EVALUASI FILTERS =====

class EvaluasiOverviewFilter(BaseModel):
    """Filter untuk overview semua data evaluasi."""
    
    # Scope
    inspektorat: Optional[str] = Field(None, description="Filter by inspektorat")
    user_perwadag_id: Optional[str] = Field(None, description="Filter by perwadag")
    tahun: Optional[int] = Field(None, ge=2020, le=2030, description="Filter by tahun")
    
    # Status
    progress_min: Optional[int] = Field(None, ge=0, le=100, description="Minimum progress")
    progress_max: Optional[int] = Field(None, ge=0, le=100, description="Maximum progress")
    is_active: Optional[bool] = Field(None, description="Filter active evaluations")
    
    # Completion status
    has_surat_pemberitahuan: Optional[bool] = None
    has_all_meetings: Optional[bool] = None
    has_matriks: Optional[bool] = None
    has_laporan: Optional[bool] = None
    has_kuisioner: Optional[bool] = None


class EvaluasiSearchFilter(BaseModel):
    """Advanced search filter untuk semua data evaluasi."""
    
    # Pagination
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(20, ge=1, le=100, description="Page size")
    
    # Global search
    search: Optional[str] = Field(None, description="Global search across all evaluasi data")
    
    # Scope filters
    inspektorat: Optional[str] = Field(None, description="Filter by inspektorat")
    tahun: Optional[int] = Field(None, ge=2020, le=2030, description="Filter by tahun")
    
    # Date range
    date_from: Optional[date] = Field(None, description="Filter from date")
    date_to: Optional[date] = Field(None, description="Filter to date")
    
    # Content type
    search_in_surat_tugas: bool = Field(True, description="Search in surat tugas")
    search_in_meetings: bool = Field(True, description="Search in meetings")
    search_in_laporan: bool = Field(True, description="Search in laporan")
    
    @field_validator('search')
    @classmethod
    def validate_search(cls, search: Optional[str]) -> Optional[str]:
        """Validate search term."""
        if search is not None:
            search = search.strip()
            if not search:
                return None
            if len(search) > 200:
                raise ValueError("Search term too long (max 200 characters)")
        return search