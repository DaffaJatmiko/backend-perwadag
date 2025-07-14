"""Models initialization - Updated dengan evaluasi models."""

# ===== EXISTING MODELS =====
from .base import BaseModel, TimestampMixin, SoftDeleteMixin, AuditMixin
from .enums import UserRole
from .user import User, PasswordResetToken

# ===== NEW EVALUASI MODELS =====

# Enums
from .evaluasi_enums import (
    MeetingType, StatusEvaluasi, FileType, 
    EvaluasiStage, FileCategory
)

# Core evaluasi models
from .surat_tugas import SuratTugas
from .surat_pemberitahuan import SuratPemberitahuan
from .meeting import Meeting
from .matriks import Matriks
from .laporan_hasil import LaporanHasil
from .kuisioner import Kuisioner
from .format_kuisioner import FormatKuisioner

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
    
    # Evaluasi enums
    "MeetingType",
    "StatusEvaluasi",
    "FileType",
    "EvaluasiStage", 
    "FileCategory",
    
    # Evaluasi models
    "SuratTugas",
    "SuratPemberitahuan",
    "Meeting",
    "Matriks",
    "LaporanHasil",
    "Kuisioner",
    "FormatKuisioner",
]

# ===== MODEL REGISTRATION FOR SQLModel =====

# Import semua models di sini akan ensure bahwa SQLModel.metadata.create_all()
# akan membuat semua tables yang dibutuhkan

# Existing tables:
# - users
# - password_reset_tokens  
# - file_uploads

# New evaluasi tables:
# - surat_tugas
# - surat_pemberitahuan
# - meetings
# - matriks
# - laporan_hasil
# - kuisioner
# - format_kuisioner

# Total: 10 tables (3 existing + 7 new evaluasi tables)

# ===== TABLE CREATION ORDER =====

"""
Table creation order (berdasarkan foreign key dependencies):

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

SQLAlchemy akan automatically handle creation order berdasarkan foreign keys.
"""

# ===== DATABASE CONSTRAINTS SUMMARY =====

"""
Key constraints yang akan dibuat:

UNIQUE CONSTRAINTS:
- users.username
- users.email (jika tidak NULL)
- password_reset_tokens.token
- surat_tugas.no_surat
- meetings: (surat_tugas_id, meeting_type) - unique combination

FOREIGN KEY CONSTRAINTS:
- password_reset_tokens.user_id -> users.id
- file_uploads.uploaded_by -> users.id
- surat_tugas.user_perwadag_id -> users.id
- surat_pemberitahuan.surat_tugas_id -> surat_tugas.id
- meetings.surat_tugas_id -> surat_tugas.id
- matriks.surat_tugas_id -> surat_tugas.id
- laporan_hasil.surat_tugas_id -> surat_tugas.id
- kuisioner.surat_tugas_id -> surat_tugas.id

INDEXES:
- Semua foreign key fields
- Search fields: nama_perwadag, inspektorat, tahun_evaluasi
- Status fields untuk filtering
"""