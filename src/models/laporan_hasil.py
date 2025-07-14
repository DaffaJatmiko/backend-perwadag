"""Model untuk laporan akhir hasil evaluasi."""

from typing import Optional
from datetime import date
from sqlmodel import Field, SQLModel
import uuid as uuid_lib

from src.models.base import BaseModel


class LaporanHasil(BaseModel, SQLModel, table=True):
    """Model untuk laporan akhir hasil evaluasi."""
    
    __tablename__ = "laporan_hasil"
    
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
    
    nomor_laporan: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Nomor laporan hasil evaluasi"
    )
    
    tanggal_laporan: Optional[date] = Field(
        default=None,
        description="Tanggal laporan"
    )
    
    file_laporan_hasil: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Path file laporan hasil"
    )
    
    def is_completed(self) -> bool:
        """Check apakah laporan hasil sudah completed."""
        return (
            self.nomor_laporan is not None and
            self.nomor_laporan.strip() != "" and
            self.tanggal_laporan is not None and
            self.file_laporan_hasil is not None and
            self.file_laporan_hasil.strip() != ""
        )
    
    def has_file(self) -> bool:
        """Check apakah sudah ada file yang diupload."""
        return self.file_laporan_hasil is not None and self.file_laporan_hasil.strip() != ""
    
    def has_nomor_laporan(self) -> bool:
        """Check apakah sudah ada nomor laporan."""
        return self.nomor_laporan is not None and self.nomor_laporan.strip() != ""
    
    def has_tanggal_laporan(self) -> bool:
        """Check apakah sudah ada tanggal laporan."""
        return self.tanggal_laporan is not None
    
    def get_completion_percentage(self) -> int:
        """Get completion percentage (0-100)."""
        completed_items = 0
        total_items = 3  # nomor, tanggal, file
        
        if self.has_nomor_laporan():
            completed_items += 1
        if self.has_tanggal_laporan():
            completed_items += 1
        if self.has_file():
            completed_items += 1
        
        return int((completed_items / total_items) * 100)
    
    def clear_file(self) -> Optional[str]:
        """Clear file and return file path for deletion."""
        if self.file_laporan_hasil:
            file_path = self.file_laporan_hasil
            self.file_laporan_hasil = None
            return file_path
        return None
    
    def __repr__(self) -> str:
        return f"<LaporanHasil(nomor={self.nomor_laporan}, surat_tugas_id={self.surat_tugas_id}, completed={self.is_completed()})>"