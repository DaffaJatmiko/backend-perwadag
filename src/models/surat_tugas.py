"""Model untuk surat tugas evaluasi."""

from typing import Optional, List
from datetime import date
from sqlmodel import Field, SQLModel, Relationship
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
    pengedali_mutu_id: Optional[str] = Field(
        default=None,
        foreign_key="users.id",
        max_length=36,
        description="ID user pengedali mutu"
    )
    pengendali_teknis_id: Optional[str] = Field(
        default=None,
        foreign_key="users.id", 
        max_length=36,
        description="ID user pengendali teknis"
    )
    ketua_tim_id: Optional[str] = Field(
        default=None,
        foreign_key="users.id",
        max_length=36, 
        description="ID user ketua tim evaluasi"
    )
    anggota_tim_ids: Optional[str] = Field(
        default=None,
        description="Comma-separated user IDs untuk anggota tim"
    )
    pimpinan_inspektorat_id: Optional[str] = Field(
        default=None,
        foreign_key="users.id",
        max_length=36,
        description="ID pimpinan inspektorat"
    )
    
    # File surat tugas
    file_surat_tugas: str = Field(
        max_length=500,
        description="Path file surat tugas yang diupload"
    )

    pengedali_mutu: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "SuratTugas.pengedali_mutu_id"}
    )
    pengendali_teknis: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "SuratTugas.pengendali_teknis_id"}
    )
    ketua_tim: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "SuratTugas.ketua_tim_id"}
    )
    pimpinan_inspektorat: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "SuratTugas.pimpinan_inspektorat_id"}
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

    def get_anggota_tim_list(self) -> List[str]:
        """Get list of anggota tim IDs."""
        if not self.anggota_tim_ids:
            return []
        return [uid.strip() for uid in self.anggota_tim_ids.split(',') if uid.strip()]

    def set_anggota_tim_list(self, user_ids: List[str]) -> None:
        """Set anggota tim dari list of user IDs."""
        self.anggota_tim_ids = ','.join(user_ids) if user_ids else None

    def is_user_assigned(self, user_id: str) -> bool:
        """Check if user is assigned to this surat tugas."""
        assigned_positions = [
            self.pengedali_mutu_id,
            self.pengendali_teknis_id, 
            self.ketua_tim_id
        ]
        
        # Check anggota tim
        anggota_tim_list = self.get_anggota_tim_list()
        assigned_positions.extend(anggota_tim_list)
        
        return user_id in [pos for pos in assigned_positions if pos]

    def get_all_assigned_user_ids(self) -> List[str]:
        """Get all assigned user IDs."""
        assigned_ids = []
        
        # Add position holders
        for user_id in [self.pengedali_mutu_id, self.pengendali_teknis_id, self.ketua_tim_id]:
            if user_id:
                assigned_ids.append(user_id)
        
        # Add anggota tim
        assigned_ids.extend(self.get_anggota_tim_list())
        
        return list(set(assigned_ids))  # Remove duplicates
    
    def __repr__(self) -> str:
        return f"<SuratTugas(no_surat={self.no_surat}, perwadag={self.nama_perwadag})>"