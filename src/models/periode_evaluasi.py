# ===== src/models/periode_evaluasi.py =====
"""Model untuk periode evaluasi."""

from typing import Optional
from sqlmodel import Field, SQLModel, Column
from sqlalchemy import Enum as SQLEnum
import uuid as uuid_lib

from src.models.base import BaseModel


class PeriodeEvaluasi(BaseModel, SQLModel, table=True):
    """Model untuk periode evaluasi penilaian risiko."""
    
    __tablename__ = "periode_evaluasi"
    
    id: str = Field(
        default_factory=lambda: str(uuid_lib.uuid4()),
        primary_key=True,
        max_length=36
    )
    
    tahun: int = Field(
        unique=True,
        index=True,
        description="Tahun periode evaluasi"
    )
    
    is_locked: bool = Field(
        default=False,
        description="Status lock periode (true = tidak bisa edit)"
    )
    
    
    def is_editable(self) -> bool:
        """Check apakah periode masih bisa diedit."""
        return not self.is_locked and self.deleted_at is None
    
    def get_tahun_pembanding(self) -> dict:
        """Generate tahun pembanding untuk kriteria."""
        return {
            "tahun_pembanding_1": self.tahun - 2,  # tahun sebelumnya
            "tahun_pembanding_2": self.tahun - 1   # tahun lalu
        }
    
    def get_lock_status_display(self) -> str:
        """Get display name untuk lock status."""
        return "Terkunci" if self.is_locked else "Dapat Diedit"
    
    def __repr__(self) -> str:
        return f"<PeriodeEvaluasi(tahun={self.tahun}, locked={self.is_locked})>"

