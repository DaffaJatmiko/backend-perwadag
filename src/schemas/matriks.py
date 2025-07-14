# ===== src/schemas/matriks.py =====
"""Schemas untuk matriks rekomendasi."""

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

from src.schemas.common import SuccessResponse


class MatriksCreate(BaseModel):
    """Schema untuk membuat matriks (auto-generated)."""
    surat_tugas_id: str = Field(..., description="ID surat tugas terkait")


class MatriksUpdate(BaseModel):
    """Schema untuk update matriks."""
    pass  # Only file upload, no other fields to update


class MatriksResponse(BaseModel):
    """Schema untuk response matriks."""
    id: str
    surat_tugas_id: str
    file_dokumen_matriks: Optional[str] = None
    file_dokumen_matriks_url: Optional[str] = None
    is_completed: bool
    has_file: bool
    completion_percentage: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class MatriksListResponse(BaseModel):
    """Schema untuk response list matriks."""
    matriks: List[MatriksResponse]
    total: int
    page: int
    size: int
    pages: int


class MatriksFileUploadResponse(SuccessResponse):
    """Schema untuk response upload file."""
    matriks_id: str
    file_path: str
    file_url: str