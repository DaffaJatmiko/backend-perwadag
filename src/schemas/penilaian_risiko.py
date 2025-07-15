# ===== src/schemas/penilaian_risiko.py =====
"""Schemas untuk penilaian risiko."""

from typing import List, Optional, Dict, Any
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime

from src.schemas.common import SuccessResponse
from src.schemas.shared import PaginationInfo


# ===== KRITERIA DATA SCHEMAS =====

class TrenCapaianData(BaseModel):
    """Data untuk kriteria tren capaian."""
    tahun_pembanding_1: int
    capaian_tahun_1: Optional[float] = None
    tahun_pembanding_2: int
    capaian_tahun_2: Optional[float] = None
    tren: Optional[float] = None
    pilihan: Optional[str] = None
    nilai: Optional[int] = None


class RealisasiAnggaranData(BaseModel):
    """Data untuk kriteria realisasi anggaran."""
    tahun_pembanding: int
    realisasi: Optional[float] = None
    pagu: Optional[float] = None
    persentase: Optional[float] = None
    pilihan: Optional[str] = None
    nilai: Optional[int] = None


class TrenEksporData(BaseModel):
    """Data untuk kriteria tren ekspor."""
    tahun_pembanding: int
    deskripsi: Optional[float] = None
    pilihan: Optional[str] = None
    nilai: Optional[int] = None


class AuditItjenData(BaseModel):
    """Data untuk kriteria audit itjen."""
    tahun_pembanding: int
    deskripsi: Optional[str] = None
    pilihan: Optional[str] = None
    nilai: Optional[int] = None


class PerjanjianPerdaganganData(BaseModel):
    """Data untuk kriteria perjanjian perdagangan."""
    tahun_pembanding: int
    deskripsi: Optional[str] = None
    pilihan: Optional[str] = None
    nilai: Optional[int] = None


class PeringkatEksporData(BaseModel):
    """Data untuk kriteria peringkat ekspor."""
    tahun_pembanding: int
    deskripsi: Optional[int] = None
    pilihan: Optional[str] = None
    nilai: Optional[int] = None


class PersentaseIkData(BaseModel):
    """Data untuk kriteria persentase IK."""
    tahun_pembanding: int
    ik_tidak_tercapai: Optional[int] = None
    total_ik: Optional[int] = None
    persentase: Optional[float] = None
    pilihan: Optional[str] = None
    nilai: Optional[int] = None


class RealisasiTeiData(BaseModel):
    """Data untuk kriteria realisasi TEI."""
    tahun_pembanding: int
    nilai_realisasi: Optional[float] = None
    nilai_potensi: Optional[float] = None
    deskripsi: Optional[float] = None
    pilihan: Optional[str] = None
    nilai: Optional[int] = None


class KriteriaDataSchema(BaseModel):
    """Schema untuk semua data kriteria."""
    tren_capaian: TrenCapaianData
    realisasi_anggaran: RealisasiAnggaranData
    tren_ekspor: TrenEksporData
    audit_itjen: AuditItjenData
    perjanjian_perdagangan: PerjanjianPerdaganganData
    peringkat_ekspor: PeringkatEksporData
    persentase_ik: PersentaseIkData
    realisasi_tei: RealisasiTeiData


# ===== REQUEST SCHEMAS =====

class PenilaianRisikoUpdate(BaseModel):
    """Schema untuk update penilaian risiko dengan auto-calculate."""
    
    kriteria_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Data kriteria penilaian"
    )
    
    catatan: Optional[str] = Field(
        None,
        max_length=1000,
        description="Catatan tambahan"
    )
    
    # NEW: Auto-calculate option
    auto_calculate: bool = Field(
        default=True,
        description="Auto calculate jika data kriteria lengkap (default: true)"
    )
    
    @field_validator('kriteria_data')
    @classmethod
    def validate_kriteria_data(cls, kriteria_data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Validate struktur kriteria data."""
        if kriteria_data is None:
            return kriteria_data
        
        # Validate struktur dasar
        required_criteria = [
            'tren_capaian', 'realisasi_anggaran', 'tren_ekspor', 'audit_itjen',
            'perjanjian_perdagangan', 'peringkat_ekspor', 'persentase_ik', 'realisasi_tei'
        ]
        
        for criteria in required_criteria:
            if criteria not in kriteria_data:
                raise ValueError(f"Kriteria '{criteria}' harus ada dalam data")
        
        return kriteria_data


class PenilaianRisikoCalculateRequest(BaseModel):
    """Schema untuk request kalkulasi penilaian risiko."""
    
    force_recalculate: bool = Field(
        default=False,
        description="Force recalculate meskipun sudah ada hasil"
    )


# ===== RESPONSE SCHEMAS =====

class PerwardagSummary(BaseModel):
    """Summary info perwadag untuk penilaian risiko."""
    
    id: str
    nama: str
    inspektorat: str
    email: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class PeriodeSummary(BaseModel):
    """Summary info periode untuk penilaian risiko."""
    
    id: str
    tahun: int
    status: str
    is_locked: bool
    is_editable: bool
    
    model_config = ConfigDict(from_attributes=True)


class PenilaianRisikoResponse(BaseModel):
    """Schema untuk response penilaian risiko."""
    
    id: str
    user_perwadag_id: str
    periode_id: str
    tahun: int
    inspektorat: str
    
    # Hasil kalkulasi
    total_nilai_risiko: Optional[Decimal] = None
    skor_rata_rata: Optional[Decimal] = None
    profil_risiko_auditan: Optional[str] = None
    catatan: Optional[str] = None
    
    # Data kriteria
    kriteria_data: Dict[str, Any]
    
    # Status information
    is_calculation_complete: bool = Field(description="Apakah data kriteria lengkap")
    has_calculation_result: bool = Field(description="Apakah sudah ada hasil kalkulasi")
    completion_percentage: int = Field(description="Persentase kelengkapan data")
    profil_risiko_color: str = Field(description="Warna untuk profil risiko")
    
    # Related data
    perwadag_info: PerwardagSummary
    periode_info: PeriodeSummary
    
    # Quick access fields
    nama_perwadag: str
    periode_tahun: int
    periode_status: str
    
    # NEW: Calculation info
    calculation_performed: bool = Field(
        default=False,
        description="Apakah kalkulasi otomatis dilakukan"
    )
    calculation_details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Detail hasil kalkulasi (jika ada)"
    )

    # Audit fields
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class PenilaianRisikoListResponse(BaseModel):
    """Schema untuk response list penilaian risiko."""
    
    penilaian_risiko: List[PenilaianRisikoResponse]
    pagination: PaginationInfo
    statistics: Optional[Dict[str, Any]] = None


class PenilaianRisikoCalculateResponse(SuccessResponse):
    """Schema untuk response kalkulasi penilaian risiko."""
    
    penilaian_risiko: PenilaianRisikoResponse
    calculation_details: Dict[str, Any] = Field(
        description="Detail hasil kalkulasi"
    )


# ===== UTILITY SCHEMAS =====

class KriteriaOptionsResponse(BaseModel):
    """Schema untuk response opsi-opsi kriteria."""
    
    audit_itjen_options: List[Dict[str, Any]]
    perjanjian_perdagangan_options: List[Dict[str, Any]]
    
    @classmethod
    def get_default_options(cls) -> "KriteriaOptionsResponse":
        """Get default options untuk dropdown criteria."""
        return cls(
            audit_itjen_options=[
                {"label": "1 Tahun", "value": "1 Tahun", "nilai": 1},
                {"label": "2 Tahun", "value": "2 Tahun", "nilai": 2},
                {"label": "3 Tahun", "value": "3 Tahun", "nilai": 3},
                {"label": "4 Tahun", "value": "4 Tahun", "nilai": 4},
                {"label": "Belum pernah diaudit", "value": "Belum pernah diaudit", "nilai": 5}
            ],
            perjanjian_perdagangan_options=[
                {"label": "Tidak ada perjanjian internasional", "value": "Tidak ada perjanjian internasional", "nilai": 1},
                {"label": "Sedang diusulkan/ Being Proposed", "value": "Sedang diusulkan/ Being Proposed", "nilai": 2},
                {"label": "Masih berproses/ on going", "value": "Masih berproses/ on going", "nilai": 3},
                {"label": "Sudah disepakati namun belum diratifikasi", "value": "Sudah disepakati namun belum diratifikasi", "nilai": 4},
                {"label": "Sudah diimplementasikan", "value": "Sudah diimplementasikan", "nilai": 5}
            ]
        )


class PenilaianRisikoStats(BaseModel):
    """Schema untuk statistik penilaian risiko."""
    
    total_penilaian: int
    penilaian_completed: int
    completion_rate: float
    
    # Breakdown by profil risiko
    profil_rendah: int
    profil_sedang: int
    profil_tinggi: int
    
    # Breakdown by inspektorat
    by_inspektorat: Dict[str, int]
    
    # Breakdown by periode
    by_periode: Dict[int, int]
    
    # Average scores
    avg_total_nilai_risiko: Optional[float] = None
    avg_skor_rata_rata: Optional[float] = None

