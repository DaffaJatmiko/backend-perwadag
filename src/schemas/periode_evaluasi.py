# ===== src/schemas/periode_evaluasi.py =====
"""Schemas untuk periode evaluasi."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime

from src.schemas.common import SuccessResponse
from src.schemas.shared import BaseListResponse


# ===== REQUEST SCHEMAS =====

class PeriodeEvaluasiCreate(BaseModel):
    """Schema untuk create periode evaluasi."""
    
    tahun: int = Field(
        ..., 
        ge=2020, 
        le=2050,
        description="Tahun periode evaluasi"
    )
    
    @field_validator('tahun')
    @classmethod
    def validate_tahun(cls, tahun: int) -> int:
        """Validate tahun range."""
        current_year = datetime.now().year
        if tahun < 2020:
            raise ValueError("Tahun minimal adalah 2020")
        if tahun > current_year + 10:
            raise ValueError(f"Tahun maksimal adalah {current_year + 10}")
        return tahun


class PeriodeEvaluasiUpdate(BaseModel):
    """Schema untuk update periode evaluasi."""
    
    is_locked: Optional[bool] = Field(
        None,
        description="Status lock periode"
    )
    


# ===== RESPONSE SCHEMAS =====

class PeriodeEvaluasiResponse(BaseModel):
    """Schema untuk response periode evaluasi."""
    
    id: str
    tahun: int
    is_locked: bool
    
    # Computed fields
    is_editable: bool = Field(description="Apakah periode bisa diedit")
    lock_status_display: str = Field(description="Display name lock status")
    tahun_pembanding_1: int = Field(description="Tahun pembanding pertama")
    tahun_pembanding_2: int = Field(description="Tahun pembanding kedua")
    
    # Statistics
    total_penilaian: int = Field(default=0, description="Total penilaian dalam periode")
    penilaian_completed: int = Field(default=0, description="Penilaian yang sudah selesai")
    completion_rate: float = Field(default=0.0, description="Persentase kelengkapan")
    
    # Audit fields
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class PeriodeEvaluasiListResponse(BaseListResponse[PeriodeEvaluasiResponse]):
    """Standardized periode evaluasi list response."""
    pass


class PeriodeEvaluasiCreateResponse(SuccessResponse):
    """Schema untuk response create periode dengan bulk generate."""
    
    periode_evaluasi: PeriodeEvaluasiResponse
    bulk_generation_summary: Dict[str, Any] = Field(
        description="Summary hasil bulk generate penilaian risiko"
    )
