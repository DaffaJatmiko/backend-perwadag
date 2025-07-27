"""Model untuk kuisioner evaluasi - UPDATED tanpa link dokumen untuk status complete."""

from typing import Optional
from datetime import date
from sqlmodel import Field, SQLModel
import uuid as uuid_lib

from src.models.base import BaseModel


class Kuisioner(BaseModel, SQLModel, table=True):
    """Model untuk kuisioner evaluasi - UPDATED."""
    
    __tablename__ = "kuisioner"
    
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
    
    tanggal_kuisioner: Optional[date] = Field(
        default=None,
        description="Tanggal pengisian kuisioner"
    )
    
    file_kuisioner: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Path file kuisioner yang diisi"
    )

    link_dokumen_data_dukung: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Link Google Drive untuk dokumen data dukung (optional)"
    )
    
    def is_completed(self) -> bool:
        """Check apakah kuisioner sudah completed - UPDATED: hanya tanggal + file."""
        return (
            self.tanggal_kuisioner is not None and
            self.file_kuisioner is not None and
            self.file_kuisioner.strip() != ""
        )
    
    def has_file(self) -> bool:
        """Check apakah sudah ada file yang diupload."""
        return self.file_kuisioner is not None and self.file_kuisioner.strip() != ""
    
    def has_tanggal(self) -> bool:
        """Check apakah sudah ada tanggal kuisioner."""
        return self.tanggal_kuisioner is not None

    def has_link_dokumen(self) -> bool:
        """Check apakah sudah ada link dokumen data dukung."""
        return self.link_dokumen_data_dukung is not None and self.link_dokumen_data_dukung.strip() != ""

    def get_completion_percentage(self) -> int:
        """Get completion percentage (0-100) - UPDATED: hanya 2 field untuk complete."""
        completed_items = 0
        total_items = 2  # CHANGED: hanya tanggal + file (tanpa link dokumen)
        
        if self.has_tanggal():
            completed_items += 1
        if self.has_file():
            completed_items += 1
        # REMOVED: link dokumen dari perhitungan completion
        
        return int((completed_items / total_items) * 100)
    
    def clear_file(self) -> Optional[str]:
        """Clear file and return file path for deletion."""
        if self.file_kuisioner:
            file_path = self.file_kuisioner
            self.file_kuisioner = None
            return file_path
        return None
    
    def __repr__(self) -> str:
        return f"<Kuisioner(tanggal={self.tanggal_kuisioner}, surat_tugas_id={self.surat_tugas_id}, completed={self.is_completed()})>"