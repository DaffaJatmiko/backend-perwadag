"""Model untuk matriks rekomendasi hasil evaluasi."""

from typing import Optional
from sqlmodel import Field, SQLModel
import uuid as uuid_lib

from src.models.base import BaseModel


class Matriks(BaseModel, SQLModel, table=True):
    """Model untuk matriks rekomendasi hasil evaluasi."""
    
    __tablename__ = "matriks"
    
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
    
    file_dokumen_matriks: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Path file matriks rekomendasi"
    )
    
    def is_completed(self) -> bool:
        """Check apakah matriks sudah completed."""
        return (
            self.file_dokumen_matriks is not None and
            self.file_dokumen_matriks.strip() != ""
        )
    
    def has_file(self) -> bool:
        """Check apakah sudah ada file yang diupload."""
        return self.file_dokumen_matriks is not None and self.file_dokumen_matriks.strip() != ""
    
    def get_completion_percentage(self) -> int:
        """Get completion percentage (0-100)."""
        return 100 if self.is_completed() else 0
    
    def clear_file(self) -> Optional[str]:
        """Clear file and return file path for deletion."""
        if self.file_dokumen_matriks:
            file_path = self.file_dokumen_matriks
            self.file_dokumen_matriks = None
            return file_path
        return None
    
    def __repr__(self) -> str:
        return f"<Matriks(surat_tugas_id={self.surat_tugas_id}, completed={self.is_completed()})>"