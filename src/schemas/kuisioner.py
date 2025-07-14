# ===== src/schemas/kuisioner.py =====
"""Schemas untuk kuisioner."""

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

from src.schemas.common import SuccessResponse


class KuisionerCreate(BaseModel):
    """Schema untuk membuat kuisioner (auto-generated)."""
    surat_tugas_id: str = Field(..., description="ID surat tugas terkait")


class KuisionerUpdate(BaseModel):
    """Schema untuk update kuisioner."""
    pass  # Only file upload, no other fields to update


class KuisionerResponse(BaseModel):
    """Schema untuk response kuisioner."""
    id: str
    surat_tugas_id: str
    file_kuisioner: Optional[str] = None
    file_kuisioner_url: Optional[str] = None
    is_completed: bool
    has_file: bool
    completion_percentage: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class KuisionerListResponse(BaseModel):
    """Schema untuk response list kuisioner."""
    kuisioner: List[KuisionerResponse]
    total: int
    page: int
    size: int
    pages: int


class KuisionerFileUploadResponse(SuccessResponse):
    """Schema untuk response upload file."""
    kuisioner_id: str
    file_path: str
    file_url: str