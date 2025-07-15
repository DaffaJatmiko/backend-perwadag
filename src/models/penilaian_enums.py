# ===== src/models/penilaian_enums.py =====
"""Enums untuk sistem penilaian risiko."""

from enum import Enum


class StatusPeriode(str, Enum):
    """Status periode evaluasi."""
    AKTIF = "aktif"
    TUTUP = "tutup"
    
    @classmethod
    def get_all_values(cls):
        """Get all status values."""
        return [status.value for status in cls]
    
    @classmethod
    def get_display_name(cls, status: str) -> str:
        """Get display name untuk status."""
        display_map = {
            cls.AKTIF.value: "Aktif",
            cls.TUTUP.value: "Tutup"
        }
        return display_map.get(status, status)


class ProfilRisiko(str, Enum):
    """Profil risiko auditan."""
    RENDAH = "Rendah"
    SEDANG = "Sedang" 
    TINGGI = "Tinggi"
    
    @classmethod
    def get_all_values(cls):
        """Get all profil risiko values."""
        return [profil.value for profil in cls]
    
    @classmethod
    def get_risk_level_numeric(cls, profil: str) -> int:
        """Get numeric level untuk sorting."""
        level_map = {
            cls.RENDAH.value: 1,
            cls.SEDANG.value: 2,
            cls.TINGGI.value: 3
        }
        return level_map.get(profil, 0)


class KriteriaPenilaian(str, Enum):
    """Enum untuk nama-nama kriteria penilaian."""
    TREN_CAPAIAN = "tren_capaian"
    REALISASI_ANGGARAN = "realisasi_anggaran"
    TREN_EKSPOR = "tren_ekspor"
    AUDIT_ITJEN = "audit_itjen"
    PERJANJIAN_PERDAGANGAN = "perjanjian_perdagangan"
    PERINGKAT_EKSPOR = "peringkat_ekspor"
    PERSENTASE_IK = "persentase_ik"
    REALISASI_TEI = "realisasi_tei"
    
    @classmethod
    def get_all_criteria(cls):
        """Get all criteria names."""
        return [criteria.value for criteria in cls]
    
    @classmethod
    def get_display_name(cls, criteria: str) -> str:
        """Get display name untuk kriteria."""
        display_map = {
            cls.TREN_CAPAIAN.value: "Tren Capaian",
            cls.REALISASI_ANGGARAN.value: "Persentase Realisasi Anggaran",
            cls.TREN_EKSPOR.value: "Tren Nilai Ekspor",
            cls.AUDIT_ITJEN.value: "Pelaksanaan Audit Itjen",
            cls.PERJANJIAN_PERDAGANGAN.value: "Perjanjian Perdagangan",
            cls.PERINGKAT_EKSPOR.value: "Peringkat Nilai Ekspor",
            cls.PERSENTASE_IK.value: "Persentase Jumlah IK Tidak Tercapai",
            cls.REALISASI_TEI.value: "Persentase Realisasi TEI"
        }
        return display_map.get(criteria, criteria)
    
    @classmethod
    def get_weight(cls, criteria: str) -> int:
        """Get bobot untuk setiap kriteria."""
        weight_map = {
            cls.TREN_CAPAIAN.value: 15,
            cls.REALISASI_ANGGARAN.value: 10,
            cls.TREN_EKSPOR.value: 15,
            cls.AUDIT_ITJEN.value: 25,
            cls.PERJANJIAN_PERDAGANGAN.value: 5,
            cls.PERINGKAT_EKSPOR.value: 10,
            cls.PERSENTASE_IK.value: 10,
            cls.REALISASI_TEI.value: 10
        }
        return weight_map.get(criteria, 0)