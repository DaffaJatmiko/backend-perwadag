"""File upload schemas."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime
from src.schemas.shared import (
    SuratTugasBasicInfo, FileMetadata, FileUrls, 
    PaginationInfo, ModuleStatistics, AuditInfo
)


class FileUploadResponse(SuccessResponse):
    """Enhanced response untuk file uploads."""
    
    file_id: str
    filename: str
    original_filename: str
    file_path: str
    file_urls: FileUrls
    file_metadata: FileMetadata
    
    model_config = ConfigDict(from_attributes=True)


class FileListResponse(BaseModel):
    """Response schema for file list."""
    files: List[FileUploadResponse]
    total: int
    skip: int
    limit: int


class MultipleFileUploadResponse(BaseModel):
    """Response schema for multiple file upload."""
    uploaded_files: List[FileUploadResponse]
    failed_files: Optional[List[Dict[str, str]]] = None
    total_uploaded: int
    total_failed: int


class FileInfoResponse(BaseModel):
    """Response schema for file info without database fields."""
    filename: str
    content_type: str
    size: int
    url: str
    key: str
    metadata: Optional[Dict[str, Any]] = None
    uploaded_at: Optional[datetime] = None


class StorageInfoResponse(BaseModel):
    """Response schema for storage configuration info."""
    provider: str
    max_file_size: int
    max_filename_length: int
    allowed_file_types: List[str]
    uploads_path: Optional[str] = None


class FileDeleteResponse(BaseModel):
    """Response schema for file deletion."""
    success: bool
    message: str
    filename: Optional[str] = None


class FileUrlResponse(BaseModel):
    """Response schema for file URL generation."""
    url: str
    expires_in: Optional[int] = None
    expires_at: Optional[datetime] = None

class FileDownloadResponse(BaseModel):
    """Response untuk file download operations."""
    
    success: bool
    filename: str
    content_type: str
    size_mb: float
    download_url: str
    expires_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class MultiFileDownloadResponse(BaseModel):
    """Response untuk multiple file downloads."""
    
    success: bool
    message: str
    files: List[FileDownloadResponse]
    zip_file_url: Optional[str] = None
    total_size_mb: float
    expires_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)