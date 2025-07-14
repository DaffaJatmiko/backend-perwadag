"""Model untuk surat pemberitahuan evaluasi."""

from typing import Optional
from datetime import date
from sqlmodel import Field, SQLModel
import uuid as uuid_lib

from src.models.base import BaseModel


class SuratPemberitahuan(BaseModel, SQLModel, table=True):
    """Model untuk surat pemberitahuan evaluasi."""
    
    __tablename__ = "surat_pemberitahuan"
    
    id: str = Field(
        default_factory=lambda: str(uuid_lib.uuid4()),
        primary_key=True,
        max_length=36
    )
    
    surat_tugas_id: str = Field(
        foreign_key="surat_tugas.id",
        index=True,
        max_length=36,
        description="ID surat tugas terkait"
    )
    
    tanggal_surat_pemberitahuan: Optional[date] = Field(
        default=None,
        description="Tanggal surat pemberitahuan"
    )
    
    file_dokumen: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Path file surat pemberitahuan"
    )
    
    def is_completed(self) -> bool:
        """Check apakah surat pemberitahuan sudah completed."""
        return (
            self.tanggal_surat_pemberitahuan is not None and
            self.file_dokumen is not None and
            self.file_dokumen.strip() != ""
        )
    
    def has_file(self) -> bool:
        """Check apakah sudah ada file yang diupload."""
        return self.file_dokumen is not None and self.file_dokumen.strip() != ""
    
    def has_date(self) -> bool:
        """Check apakah sudah ada tanggal."""
        return self.tanggal_surat_pemberitahuan is not None
    
    def get_completion_percentage(self) -> int:
        """Get completion percentage (0-100)."""
        completed_items = 0
        total_items = 2
        
        if self.has_date():
            completed_items += 1
        if self.has_file():
            completed_items += 1
        
        return int((completed_items / total_items) * 100)
    
    def __repr__(self) -> str:
        return f"<SuratPemberitahuan(surat_tugas_id={self.surat_tugas_id}, completed={self.is_completed()})>"