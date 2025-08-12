# ===== src/models/__init__.py (UPDATE EXISTING) =====
"""Models initialization - Updated dengan penilaian risiko models."""

# ===== EXISTING MODELS =====
from .base import BaseModel, TimestampMixin, SoftDeleteMixin, AuditMixin
from .enums import UserRole
from .user import User, PasswordResetToken

# ===== EXISTING EVALUASI MODELS =====

# Enums
from .evaluasi_enums import (
    MeetingType, StatusEvaluasi, FileType, 
    EvaluasiStage, FileCategory, MatriksStatus, TindakLanjutStatus
)

# Core evaluasi models
from .surat_tugas import SuratTugas
from .surat_pemberitahuan import SuratPemberitahuan
from .meeting import Meeting
from .matriks import Matriks
from .laporan_hasil import LaporanHasil
from .kuisioner import Kuisioner
from .format_kuisioner import FormatKuisioner

# ===== NEW PENILAIAN RISIKO MODELS =====

# Penilaian risiko enums
from .penilaian_enums import (
     ProfilRisiko, KriteriaPenilaian
)

# Penilaian risiko models
from .periode_evaluasi import PeriodeEvaluasi
from .penilaian_risiko import PenilaianRisiko

# ===== LOG ACTIVITY MODEL =====
from .log_activity import LogActivity

# ===== EXPORTS =====

__all__ = [
    # Base classes
    "BaseModel",
    "TimestampMixin", 
    "SoftDeleteMixin",
    "AuditMixin",
    
    # Existing models
    "UserRole",
    "User",
    "PasswordResetToken", 
    
    # Existing evaluasi enums
    "MeetingType",
    "StatusEvaluasi",
    "FileType",
    "EvaluasiStage", 
    "FileCategory",
    "MatriksStatus",
    "TindakLanjutStatus",
    
    # Existing evaluasi models
    "SuratTugas",
    "SuratPemberitahuan",
    "Meeting",
    "Matriks",
    "LaporanHasil",
    "Kuisioner",
    "FormatKuisioner",
    
    # New penilaian risiko enums
    "ProfilRisiko",
    "KriteriaPenilaian",
    
    # New penilaian risiko models
    "PeriodeEvaluasi",
    "PenilaianRisiko",

    "LogActivity",  # Assuming LogActivity is also a model in this context
]

# ===== MODEL REGISTRATION FOR SQLModel =====

# Import semua models di sini akan ensure bahwa SQLModel.metadata.create_all()
# akan membuat semua tables yang dibutuhkan

# Existing tables:
# - users
# - password_reset_tokens  
# - file_uploads
# - surat_tugas
# - surat_pemberitahuan
# - meetings
# - matriks
# - laporan_hasil
# - kuisioner
# - format_kuisioner

# New penilaian risiko tables:
# - periode_evaluasi
# - penilaian_risiko

# Total: 12 tables (10 existing + 2 new penilaian risiko tables)

# ===== TABLE CREATION ORDER =====

"""
Updated table creation order (berdasarkan foreign key dependencies):

1. users (no dependencies)
2. password_reset_tokens (depends on users)
3. file_uploads (depends on users) 
4. surat_tugas (depends on users)
5. surat_pemberitahuan (depends on surat_tugas)
6. meetings (depends on surat_tugas)
7. matriks (depends on surat_tugas)
8. laporan_hasil (depends on surat_tugas)
9. kuisioner (depends on surat_tugas)
10. format_kuisioner (no dependencies - master table)
11. periode_evaluasi (no dependencies - master table)
12. penilaian_risiko (depends on users, periode_evaluasi)

SQLAlchemy akan automatically handle creation order berdasarkan foreign keys.
"""

# ===== DATABASE CONSTRAINTS SUMMARY =====

"""
Updated key constraints yang akan dibuat:

UNIQUE CONSTRAINTS:
- users.username
- users.email (jika tidak NULL)
- password_reset_tokens.token
- surat_tugas.no_surat
- meetings: (surat_tugas_id, meeting_type) - unique combination
- periode_evaluasi.tahun - unique tahun
- penilaian_risiko: (user_perwadag_id, periode_id) - unique combination

FOREIGN KEY CONSTRAINTS:
[Existing constraints...]
- penilaian_risiko.user_perwadag_id -> users.id
- penilaian_risiko.periode_id -> periode_evaluasi.id (CASCADE DELETE)

INDEXES:
[Existing indexes...]
- periode_evaluasi.tahun, periode_evaluasi.status, periode_evaluasi.is_locked
- penilaian_risiko.user_perwadag_id, penilaian_risiko.periode_id, penilaian_risiko.inspektorat
- penilaian_risiko.tahun, penilaian_risiko.profil_risiko_auditan
"""
