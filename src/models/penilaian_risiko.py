# ===== src/models/penilaian_risiko.py =====
"""Model untuk penilaian risiko."""

from typing import Optional, Dict, Any
from decimal import Decimal
from sqlmodel import Field, SQLModel, Column, JSON
import uuid as uuid_lib

from src.models.base import BaseModel


class PenilaianRisiko(BaseModel, SQLModel, table=True):
    """Model untuk penilaian risiko perwadag."""
    
    __tablename__ = "penilaian_risiko"
    
    id: str = Field(
        default_factory=lambda: str(uuid_lib.uuid4()),
        primary_key=True,
        max_length=36
    )
    
    # Foreign Keys
    user_perwadag_id: str = Field(
        foreign_key="users.id",
        index=True,
        max_length=36,
        description="ID user perwadag yang dinilai"
    )
    
    periode_id: str = Field(
        foreign_key="periode_evaluasi.id",
        index=True,
        max_length=36,
        description="ID periode evaluasi"
    )
    
    # Data copy untuk optimasi query
    tahun: int = Field(
        index=True,
        description="Copy tahun dari periode evaluasi"
    )
    
    inspektorat: str = Field(
        max_length=100,
        index=True,
        description="Copy inspektorat dari user perwadag"
    )
    
    # Hasil kalkulasi
    total_nilai_risiko: Optional[Decimal] = Field(
        default=None,
        max_digits=10,
        decimal_places=2,
        description="Total nilai risiko setelah kalkulasi"
    )
    
    skor_rata_rata: Optional[Decimal] = Field(
        default=None,
        max_digits=5,
        decimal_places=2,
        description="Skor rata-rata dari 8 kriteria"
    )
    
    profil_risiko_auditan: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Profil risiko: Rendah/Sedang/Tinggi"
    )
    
    catatan: Optional[str] = Field(
        default=None,
        description="Catatan tambahan penilaian"
    )
    
    # Data kriteria dalam format JSON
    kriteria_data: Dict[str, Any] = Field(
        sa_column=Column(JSON),
        description="Data 8 kriteria penilaian dalam format JSON"
    )
    
    # Table constraints akan ditambahkan di migration
    # UNIQUE KEY unique_perwadag_periode (user_perwadag_id, periode_id)
    
    @property
    def nama_perwadag(self) -> str:
        """Get nama perwadag dari relasi (akan diimplementasi di service)."""
        # Akan di-populate dari join query di repository
        return getattr(self, '_nama_perwadag', '')
    
    def is_calculation_complete(self) -> bool:
        """Check apakah semua kriteria sudah lengkap untuk kalkulasi."""
        if not self.kriteria_data:
            return False
        
        required_criteria = [
            'tren_capaian', 'realisasi_anggaran', 'tren_ekspor', 'audit_itjen',
            'perjanjian_perdagangan', 'peringkat_ekspor', 'persentase_ik', 'realisasi_tei'
        ]
        
        for criteria in required_criteria:
            if criteria not in self.kriteria_data:
                return False
            
            criteria_data = self.kriteria_data[criteria]
            if not criteria_data.get('nilai'):
                return False
        
        return True
    
    def get_profil_risiko_color(self) -> str:
        """Get warna untuk profil risiko."""
        color_map = {
            "Rendah": "green",
            "Sedang": "yellow", 
            "Tinggi": "red"
        }
        return color_map.get(self.profil_risiko_auditan, "gray")
    
    def get_completion_percentage(self) -> int:
        """Get persentase kelengkapan data kriteria."""
        if not self.kriteria_data:
            return 0
        
        required_criteria = [
            'tren_capaian', 'realisasi_anggaran', 'tren_ekspor', 'audit_itjen',
            'perjanjian_perdagangan', 'peringkat_ekspor', 'persentase_ik', 'realisasi_tei'
        ]
        
        completed = 0
        for criteria in required_criteria:
            if criteria in self.kriteria_data:
                criteria_data = self.kriteria_data[criteria]
                if criteria_data.get('nilai'):
                    completed += 1
        
        return int((completed / len(required_criteria)) * 100)
    
    def has_calculation_result(self) -> bool:
        """Check apakah sudah ada hasil kalkulasi."""
        return (
            self.total_nilai_risiko is not None and 
            self.skor_rata_rata is not None and 
            self.profil_risiko_auditan is not None
        )
    
    def __repr__(self) -> str:
        return f"<PenilaianRisiko(perwadag_id={self.user_perwadag_id}, tahun={self.tahun}, profil={self.profil_risiko_auditan})>"

