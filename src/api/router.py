"""Updated API router configuration dengan evaluasi endpoints."""

from fastapi import APIRouter

# Existing imports
from src.api.endpoints import auth, users

# New evaluasi imports
from src.api.endpoints import (
    surat_tugas, meeting, surat_pemberitahuan,
    matriks, laporan_hasil, kuisioner, format_kuisioner, periode_evaluasi, penilaian_risiko,
    email_templates, log_activity
)

# Create main API router
api_router = APIRouter()

# ===== EXISTING ENDPOINTS =====

# Include existing endpoint routers dengan proper tags dan descriptions
api_router.include_router(
    auth.router, 
    prefix="/auth", 
    tags=["Authentication"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        422: {"description": "Validation Error"},
    }
)

api_router.include_router(
    users.router, 
    prefix="/users", 
    tags=["User Management"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "User not found"},
        422: {"description": "Validation Error"},
    }
)

# ===== NEW EVALUASI ENDPOINTS =====

# Surat Tugas - Main evaluation workflow
api_router.include_router(
    surat_tugas.router,
    prefix="/evaluasi/surat-tugas",
    tags=["Evaluasi - Surat Tugas"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden - Insufficient permissions"},
        404: {"description": "Surat tugas not found"},
        422: {"description": "Validation Error"},
    }
)

# Meetings - Multiple file support
api_router.include_router(
    meeting.router,
    prefix="/evaluasi/meeting",
    tags=["Evaluasi - Meeting"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden - Admin/Inspektorat only for write operations"},
        404: {"description": "Meeting not found"},
        413: {"description": "File too large"},
        422: {"description": "Validation Error"},
    }
)

# Surat Pemberitahuan - Auto-generated documents
api_router.include_router(
    surat_pemberitahuan.router,
    prefix="/evaluasi/surat-pemberitahuan",
    tags=["Evaluasi - Surat Pemberitahuan"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden - Admin/Inspektorat only for write operations"},
        404: {"description": "Surat pemberitahuan not found"},
        422: {"description": "Validation Error"},
    }
)

# Matriks - Recommendation matrix
api_router.include_router(
    matriks.router,
    prefix="/evaluasi/matriks",
    tags=["Evaluasi - Matriks"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden - Admin/Inspektorat only for write operations"},
        404: {"description": "Matriks not found"},
        422: {"description": "Validation Error"},
    }
)

# Laporan Hasil - Final reports (Perwadag can edit)
api_router.include_router(
    laporan_hasil.router,
    prefix="/evaluasi/laporan-hasil",
    tags=["Evaluasi - Laporan Hasil"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden - Check role permissions"},
        404: {"description": "Laporan hasil not found"},
        422: {"description": "Validation Error"},
    }
)

# Kuisioner - Questionnaires (Perwadag can upload)
api_router.include_router(
    kuisioner.router,
    prefix="/evaluasi/kuisioner",
    tags=["Evaluasi - Kuisioner"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden - Check role permissions"},
        404: {"description": "Kuisioner not found"},
        422: {"description": "Validation Error"},
    }
)

# Format Kuisioner - Master templates (Admin only)
api_router.include_router(
    format_kuisioner.router,
    prefix="/evaluasi/format-kuisioner",
    tags=["Evaluasi - Format Kuisioner (Admin Only)"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden - Admin only"},
        404: {"description": "Format kuisioner not found"},
        422: {"description": "Validation Error"},
    }
)

# Penilaian Risiko - Periode Evaluasi
api_router.include_router(
    periode_evaluasi.router,
    prefix="/periode-evaluasi",
    tags=["Penilaian Risiko - Periode Evaluasi"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden - Admin only for write operations"},
        404: {"description": "Periode evaluasi not found"},
        422: {"description": "Validation Error"},
    }
)

# Penilaian Risiko - Penilaian
api_router.include_router(
    penilaian_risiko.router,
    prefix="/penilaian-risiko",
    tags=["Penilaian Risiko - Penilaian"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden - Admin/Inspektorat only"},
        404: {"description": "Penilaian risiko not found"},
        422: {"description": "Validation Error"},
    }
)

# Email Templates - Admin management with composition service
api_router.include_router(
    email_templates.router,
    prefix="/email-templates",
    tags=["Email Templates"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden - Admin only for management"},
        404: {"description": "Email template not found"},
        422: {"description": "Validation Error"},
    }
)

api_router.include_router(
    log_activity.router,
    prefix="/log-activity",
    tags=["Log Activity"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden - Admin/Inspektorat only for most operations"},
        404: {"description": "Log activity not found"},
        422: {"description": "Validation Error"},
    }
)

# ===== DOCUMENTATION METADATA =====

# Update tags metadata untuk better documentation
tags_metadata = [
    {
        "name": "Authentication",
        "description": "Authentication endpoints dengan JWT tokens dan password reset",
    },
    {
        "name": "User Management", 
        "description": "User CRUD operations dengan role-based access control",
    },
    {
        "name": "Evaluasi - Surat Tugas",
        "description": """
        **Main evaluation workflow endpoints**
        
        - Auto-generate semua related records saat create
        - Role-based access: Admin & Inspektorat dapat CRUD
        - Cascade delete functionality
        - Progress tracking dan statistics
        - Dashboard summaries
        """,
    },
    {
        "name": "Evaluasi - Meetings",
        "description": """
        **Meeting management dengan multiple file support**
        
        - 3 types: Entry, Konfirmasi, Exit
        - Multiple file upload untuk bukti hadir
        - Role-based access: Admin & Inspektorat untuk edit
        - JSON storage untuk file metadata
        """,
    },
    {
        "name": "Evaluasi - Surat Pemberitahuan",
        "description": """
        **Auto-generated notification documents**
        
        - Created automatically via surat tugas workflow
        - Simple file upload functionality
        - Role-based access: Admin & Inspektorat untuk edit
        """,
    },
    {
        "name": "Evaluasi - Matriks",
        "description": """
        **Recommendation matrix documents**
        
        - Auto-generated via surat tugas workflow
        - File upload untuk matriks rekomendasi
        - Role-based access: Admin & Inspektorat untuk edit
        """,
    },
    {
        "name": "Evaluasi - Laporan Hasil",
        "description": """
        **Final evaluation reports**
        
        - Auto-generated via surat tugas workflow
        - **Special access**: Perwadag dapat full edit milik sendiri
        - Nomor laporan, tanggal, dan file upload
        """,
    },
    {
        "name": "Evaluasi - Kuisioner",
        "description": """
        **Evaluation questionnaires**
        
        - Auto-generated via surat tugas workflow
        - **Special access**: Perwadag dapat upload file milik sendiri
        - Integration dengan format templates
        """,
    },
    {
        "name": "Evaluasi - Format Kuisioner (Admin Only)",
        "description": """
        **Master questionnaire templates**
        
        - **Admin only**: Template management
        - Year-based organization
        - Download functionality untuk templates
        - Statistics dan monitoring
        """,
    },
]

# Update tags_metadata untuk include new tags
new_tags_metadata = [
    {
        "name": "Penilaian Risiko - Periode Evaluasi",
        "description": """
        **Periode evaluasi management endpoints**
        
        - Auto-bulk generate penilaian risiko saat create periode
        - Lock/unlock mechanism untuk editing control
        - Cascade delete functionality
        - Tahun pembanding auto-generate
        - Statistics dan monitoring
        """,
    },
    {
        "name": "Penilaian Risiko - Penilaian",
        "description": """
        **Penilaian risiko management dengan 8 kriteria**
        
        - Role-based access: Admin & Inspektorat
        - Auto-calculation untuk kriteria dengan business rules
        - Total nilai risiko calculation dengan weighted scoring
        - Profil risiko determination (Rendah/Sedang/Tinggi)
        - Comprehensive filtering dan statistics
        - Bulk operations untuk efficiency
        """,
    },
    {
        "name": "Email Templates",
        "description": """
        **Email template management dengan variable replacement**
        
        - **Admin only**: Template management (CRUD operations)
        - Variable-based email composition untuk laporan hasil
        - Only one active template at a time
        - Real-time variable replacement dengan laporan data
        - Gmail integration untuk compose URLs
        - Available variables: nama_perwadag, inspektorat, tahun_evaluasi, dll
        """,
    },
]

# Extend existing tags_metadata
tags_metadata.extend(new_tags_metadata)

# Export untuk main.py
def get_api_router():
    """Get configured API router dengan semua endpoints."""
    return api_router

def get_tags_metadata():
    """Get tags metadata untuk OpenAPI documentation."""
    return tags_metadata