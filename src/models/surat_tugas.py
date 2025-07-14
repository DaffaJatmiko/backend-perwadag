"""Model untuk surat tugas evaluasi."""

from typing import Optional
from datetime import date
from sqlmodel import Field, SQLModel
import uuid as uuid_lib

from src.models.base import BaseModel


class SuratTugas(BaseModel, SQLModel, table=True):
    """Model untuk surat tugas evaluasi perwadag."""
    
    __tablename__ = "surat_tugas"
    
    id: str = Field(
        default_factory=lambda: str(uuid_lib.uuid4()),
        primary_key=True,
        max_length=36
    )
    
    # Foreign Key ke Users (perwadag)
    user_perwadag_id: str = Field(
        foreign_key="users.id",
        index=True,
        max_length=36,
        description="ID user perwadag yang dievaluasi"
    )
    
    # Data copy dari users untuk optimasi query
    nama_perwadag: str = Field(
        max_length=200,
        index=True,
        description="Copy dari users.nama untuk optimasi query"
    )
    inspektorat: str = Field(
        max_length=100,
        index=True,
        description="Copy dari users.inspektorat untuk optimasi query"
    )
    
    # Data evaluasi
    tanggal_evaluasi_mulai: date = Field(
        index=True,
        description="Tanggal mulai evaluasi"
    )
    tanggal_evaluasi_selesai: date = Field(
        description="Tanggal selesai evaluasi"
    )
    
    # Data surat tugas
    no_surat: str = Field(
        max_length=100,
        unique=True,
        index=True,
        description="Nomor surat tugas"
    )
    
    # Data tim evaluasi
    nama_pengedali_mutu: str = Field(
        max_length=200,
        description="Nama pengedali mutu"
    )
    nama_pengendali_teknis: str = Field(
        max_length=200,
        description="Nama pengendali teknis"
    )
    nama_ketua_tim: str = Field(
        max_length=200,
        description="Nama ketua tim evaluasi"
    )
    
    # File surat tugas
    file_surat_tugas: str = Field(
        max_length=500,
        description="Path file surat tugas yang diupload"
    )
    
    @property
    def tahun_evaluasi(self) -> int:
        """Get tahun evaluasi dari tanggal mulai."""
        return self.tanggal_evaluasi_mulai.year
    
    @property
    def durasi_evaluasi(self) -> int:
        """Get durasi evaluasi dalam hari."""
        return (self.tanggal_evaluasi_selesai - self.tanggal_evaluasi_mulai).days + 1
    
    def is_evaluation_active(self) -> bool:
        """Check apakah evaluasi sedang berlangsung."""
        from datetime import date
        today = date.today()
        return self.tanggal_evaluasi_mulai <= today <= self.tanggal_evaluasi_selesai
    
    def is_evaluation_upcoming(self) -> bool:
        """Check apakah evaluasi akan datang."""
        from datetime import date
        today = date.today()
        return self.tanggal_evaluasi_mulai > today
    
    def is_evaluation_completed(self) -> bool:
        """Check apakah evaluasi sudah selesai."""
        from datetime import date
        today = date.today()
        return self.tanggal_evaluasi_selesai < today
    
    def get_evaluation_status(self) -> str:
        """Get status evaluasi berdasarkan tanggal."""
        if self.is_evaluation_upcoming():
            return "upcoming"
        elif self.is_evaluation_active():
            return "active"
        else:
            return "completed"
    
    def __repr__(self) -> str:
        return f"<SuratTugas(no_surat={self.no_surat}, perwadag={self.nama_perwadag})>"