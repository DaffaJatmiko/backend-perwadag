# ===== src/schemas/laporan_hasil.py =====
"""Schemas untuk laporan hasil evaluasi."""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime, date

from src.schemas.common import SuccessResponse


class LaporanHasilCreate(BaseModel):
    """Schema untuk membuat laporan hasil (auto-generated)."""
    surat_tugas_id: str = Field(..., description="ID surat tugas terkait")


class LaporanHasilUpdate(BaseModel):
    """Schema untuk update laporan hasil."""
    nomor_laporan: Optional[str] = Field(None, max_length=100)
    tanggal_laporan: Optional[date] = None
    
    @field_validator('nomor_laporan')
    @classmethod
    def validate_nomor_laporan(cls, nomor_laporan: Optional[str]) -> Optional[str]:
        """Validate nomor laporan."""
        if nomor_laporan is not None:
            nomor_laporan = nomor_laporan.strip()
            if not nomor_laporan:
                raise ValueError("Nomor laporan tidak boleh kosong")
        return nomor_laporan


class LaporanHasilResponse(BaseModel):
    """Schema untuk response laporan hasil."""
    id: str
    surat_tugas_id: str
    nomor_laporan: Optional[str] = None
    tanggal_laporan: Optional[date] = None
    file_laporan_hasil: Optional[str] = None
    file_laporan_hasil_url: Optional[str] = None
    is_completed: bool
    has_file: bool
    has_nomor_laporan: bool
    has_tanggal_laporan: bool
    completion_percentage: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class LaporanHasilListResponse(BaseModel):
    """Schema untuk response list laporan hasil."""
    laporan_hasil: List[LaporanHasilResponse]
    total: int
    page: int
    size: int
    pages: int


class LaporanHasilFileUploadResponse(SuccessResponse):
    """Schema untuk response upload file."""
    laporan_hasil_id: str
    file_path: str
    file_url: str