"""API endpoints untuk surat tugas dengan auto-generate workflow."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, Form
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.repositories.surat_tugas import SuratTugasRepository
from src.repositories.surat_pemberitahuan import SuratPemberitahuanRepository
from src.repositories.meeting import MeetingRepository
from src.repositories.matriks import MatriksRepository
from src.repositories.laporan_hasil import LaporanHasilRepository
from src.repositories.kuisioner import KuisionerRepository
from src.services.surat_tugas import SuratTugasService
from src.schemas.surat_tugas import (
    SuratTugasCreate, SuratTugasUpdate, SuratTugasResponse,
    SuratTugasListResponse, SuratTugasCreateResponse, SuratTugasOverview,
    SuratTugasStats
)
from src.schemas.filters import SuratTugasFilterParams
from src.schemas.common import SuccessResponse
from src.auth.evaluasi_permissions import (
    require_evaluasi_read_access, require_surat_tugas_create_access,
    require_evaluasi_write_access, require_surat_tugas_delete_access,
    require_statistics_access, get_evaluasi_filter_scope
)

router = APIRouter()


async def get_surat_tugas_service(session: AsyncSession = Depends(get_db)) -> SuratTugasService:
    """Dependency untuk SuratTugasService."""
    surat_tugas_repo = SuratTugasRepository(session)
    surat_pemberitahuan_repo = SuratPemberitahuanRepository(session)
    meeting_repo = MeetingRepository(session)
    matriks_repo = MatriksRepository(session)
    laporan_hasil_repo = LaporanHasilRepository(session)
    kuisioner_repo = KuisionerRepository(session)
    
    return SuratTugasService(
        surat_tugas_repo,
        surat_pemberitahuan_repo,
        meeting_repo,
        matriks_repo,
        laporan_hasil_repo,
        kuisioner_repo
    )


# ===== CREATE WITH AUTO-GENERATE =====

@router.post("/", response_model=SuratTugasCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_surat_tugas(
    user_perwadag_id: str = Form(..., description="ID perwadag yang dievaluasi"),
    tanggal_evaluasi_mulai: str = Form(..., description="Tanggal mulai (YYYY-MM-DD)"),
    tanggal_evaluasi_selesai: str = Form(..., description="Tanggal selesai (YYYY-MM-DD)"),
    no_surat: str = Form(..., description="Nomor surat tugas"),
    nama_pengedali_mutu: str = Form(..., description="Nama pengedali mutu"),
    nama_pengendali_teknis: str = Form(..., description="Nama pengendali teknis"),
    nama_ketua_tim: str = Form(..., description="Nama ketua tim"),
    file: UploadFile = File(..., description="File surat tugas"),
    current_user: dict = Depends(require_surat_tugas_create_access()),
    surat_tugas_service: SuratTugasService = Depends(get_surat_tugas_service)
):
    """
    Create surat tugas baru dengan AUTO-GENERATE semua related records.
    
    **Accessible by**: Admin dan Inspektorat
    
    **Auto-Generate Process**:
    1. Upload file surat tugas
    2. Create surat tugas record
    3. AUTO-GENERATE 6 related records:
       - 1x surat_pemberitahuan (empty)
       - 3x meetings (entry, konfirmasi, exit - all empty)
       - 1x matriks (empty)
       - 1x laporan_hasil (empty)
       - 1x kuisioner (empty)
    
    **Requirements**:
    - user_perwadag_id harus valid dan active
    - no_surat harus unique
    - file harus format yang didukung (PDF, DOC, DOCX)
    
    **Returns**: Complete surat tugas data dengan IDs semua generated records
    """
    from datetime import datetime
    
    # Parse dates
    try:
        tanggal_mulai = datetime.strptime(tanggal_evaluasi_mulai, "%Y-%m-%d").date()
        tanggal_selesai = datetime.strptime(tanggal_evaluasi_selesai, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD"
        )
    
    # Build create data
    surat_tugas_data = SuratTugasCreate(
        user_perwadag_id=user_perwadag_id,
        tanggal_evaluasi_mulai=tanggal_mulai,
        tanggal_evaluasi_selesai=tanggal_selesai,
        no_surat=no_surat,
        nama_pengedali_mutu=nama_pengedali_mutu,
        nama_pengendali_teknis=nama_pengendali_teknis,
        nama_ketua_tim=nama_ketua_tim
    )
    
    return await surat_tugas_service.create_surat_tugas(
        surat_tugas_data, file, current_user["id"]
    )


# ===== READ OPERATIONS =====

@router.get("/", response_model=SuratTugasListResponse)
async def get_all_surat_tugas(
    filters: SuratTugasFilterParams = Depends(),
    current_user: dict = Depends(require_evaluasi_read_access()),
    surat_tugas_service: SuratTugasService = Depends(get_surat_tugas_service)
):
    """
    Get all surat tugas dengan comprehensive filtering.
    
    **Accessible by**: Semua roles dengan scope filtering:
    - **Admin**: Lihat semua surat tugas
    - **Inspektorat**: Lihat surat tugas di wilayah kerjanya
    - **Perwadag**: Lihat surat tugas milik sendiri only
    
    **Query Parameters**:
    - page, size: Pagination
    - search: Search dalam nama_perwadag, no_surat, nama tim
    - inspektorat: Filter by inspektorat
    - tahun_evaluasi: Filter by tahun
    - is_active: Filter evaluasi yang sedang berlangsung
    - has_file: Filter by file upload status
    - is_completed: Filter by completion status
    
    **Returns**: Paginated list dengan progress tracking setiap evaluasi
    """
    filter_scope = get_evaluasi_filter_scope(current_user)
    
    return await surat_tugas_service.get_all_surat_tugas(
        filters,
        filter_scope["user_role"],
        filter_scope.get("user_inspektorat"),
        filter_scope.get("user_id")
    )


@router.get("/{surat_tugas_id}", response_model=SuratTugasResponse)
async def get_surat_tugas(
    surat_tugas_id: str,
    current_user: dict = Depends(require_evaluasi_read_access()),
    surat_tugas_service: SuratTugasService = Depends(get_surat_tugas_service)
):
    """
    Get surat tugas by ID dengan progress tracking.
    
    **Access Control**: Role-based dengan ownership validation di service layer
    
    **Returns**: Complete surat tugas data dengan progress dari semua related records
    """
    # Ownership validation akan dilakukan di service layer
    return await surat_tugas_service.get_surat_tugas_or_404(surat_tugas_id)


# @router.get("/{surat_tugas_id}/overview", response_model=SuratTugasOverview)
# async def get_surat_tugas_overview(
#     surat_tugas_id: str,
#     current_user: dict = Depends(require_evaluasi_read_access()),
#     surat_tugas_service: SuratTugasService = Depends(get_surat_tugas_service)
# ):
#     """
#     Get complete overview surat tugas dengan SEMUA related data.
    
#     **Returns**: 
#     - Surat tugas data
#     - Surat pemberitahuan data
#     - All 3 meetings data
#     - Matriks data
#     - Laporan hasil data
#     - Kuisioner data
    
#     **Use case**: Detail page yang menampilkan semua informasi evaluasi
#     """
#     return await surat_tugas_service.get_surat_tugas_overview(surat_tugas_id)


# ===== UPDATE OPERATIONS =====

@router.put("/{surat_tugas_id}", response_model=SuratTugasResponse)
async def update_surat_tugas(
    surat_tugas_id: str,
    surat_tugas_data: SuratTugasUpdate,
    current_user: dict = Depends(require_evaluasi_write_access()),
    surat_tugas_service: SuratTugasService = Depends(get_surat_tugas_service)
):
    """
    Update surat tugas information.
    
    **Accessible by**: Admin dan Inspektorat
    
    **Updatable fields**:
    - tanggal_evaluasi_mulai, tanggal_evaluasi_selesai
    - no_surat (harus unique)
    - nama_pengedali_mutu, nama_pengendali_teknis, nama_ketua_tim
    
    **Note**: File surat tugas diupdate via endpoint terpisah
    """
    return await surat_tugas_service.update_surat_tugas(
        surat_tugas_id, surat_tugas_data, current_user["id"]
    )


@router.post("/{surat_tugas_id}/upload-file", response_model=SuccessResponse)
async def upload_surat_tugas_file(
    surat_tugas_id: str,
    file: UploadFile = File(..., description="File surat tugas baru"),
    current_user: dict = Depends(require_evaluasi_write_access()),
    surat_tugas_service: SuratTugasService = Depends(get_surat_tugas_service)
):
    """
    Upload atau replace file surat tugas.
    
    **Accessible by**: Admin dan Inspektorat
    
    **File Requirements**:
    - Format: PDF, DOC, DOCX
    - Max size: 10MB
    
    **Behavior**: Replace existing file jika ada
    """
    return await surat_tugas_service.upload_surat_tugas_file(
        surat_tugas_id, file, current_user["id"]
    )


# ===== DELETE OPERATIONS =====

@router.delete("/{surat_tugas_id}", response_model=SuccessResponse)
async def delete_surat_tugas(
    surat_tugas_id: str,
    current_user: dict = Depends(require_surat_tugas_delete_access()),
    surat_tugas_service: SuratTugasService = Depends(get_surat_tugas_service)
):
    """
    Delete surat tugas dengan CASCADE DELETE semua related records.
    
    **Accessible by**: Admin dan Inspektorat
    
    **CASCADE DELETE Process**:
    1. Get all file paths dari surat tugas dan related records
    2. Delete all files from storage
    3. Soft delete all related records:
       - surat_pemberitahuan
       - meetings (all 3 types)
       - matriks
       - laporan_hasil
       - kuisioner
    4. Soft delete surat tugas
    
    **Warning**: This action cannot be undone!
    """
    return await surat_tugas_service.delete_surat_tugas(
        surat_tugas_id, current_user["role"], current_user["id"]
    )


# ===== STATISTICS & REPORTS =====

# @router.get("/statistics/overview", response_model=SuratTugasStats)
# async def get_surat_tugas_statistics(
#     current_user: dict = Depends(require_statistics_access()),
#     surat_tugas_service: SuratTugasService = Depends(get_surat_tugas_service)
# ):
#     """
#     Get comprehensive statistics surat tugas.
    
#     **Role-based Statistics**:
#     - **Admin**: Statistics semua surat tugas
#     - **Inspektorat**: Statistics untuk wilayah kerjanya
#     - **Perwadag**: Statistics milik sendiri
    
#     **Returns**:
#     - Total surat tugas
#     - Breakdown by tahun
#     - Breakdown by inspektorat (admin only)
#     - Evaluasi status (completed, in_progress, upcoming)
#     - Completion rate
#     """
#     filter_scope = get_evaluasi_filter_scope(current_user)
    
#     return await surat_tugas_service.get_statistics(
#         filter_scope["user_role"],
#         filter_scope.get("user_inspektorat"),
#         filter_scope.get("user_id")
#     )


# ===== UTILITY ENDPOINTS =====

# @router.get("/check/no-surat-availability")
# async def check_no_surat_availability(
#     no_surat: str = Query(..., description="Nomor surat yang akan dicek"),
#     exclude_id: Optional[str] = Query(None, description="ID yang dikecualikan (untuk update)"),
#     current_user: dict = Depends(require_surat_tugas_create_access()),
#     session: AsyncSession = Depends(get_db)
# ):
#     """
#     Check availability nomor surat.
    
#     **Use case**: Validation saat create/update surat tugas
    
#     **Returns**: 
#     - available: true/false
#     - message: explanation
#     """
#     surat_tugas_repo = SuratTugasRepository(session)
    
#     exists = await surat_tugas_repo.no_surat_exists(no_surat, exclude_id)
    
#     return {
#         "no_surat": no_surat,
#         "available": not exists,
#         "message": "Nomor surat available" if not exists else "Nomor surat already exists"
#     }


@router.get("/perwadag/list")
async def get_available_perwadag(
    current_user: dict = Depends(require_surat_tugas_create_access()),
    session: AsyncSession = Depends(get_db)
):
    """
    Get list available perwadag untuk create surat tugas.
    
    **Accessible by**: Admin dan Inspektorat
    
    **Returns**: List active perwadag users dengan basic info
    """
    from src.repositories.user import UserRepository
    from src.models.enums import UserRole
    
    user_repo = UserRepository(session)
    
    # Get all active perwadag users
    from sqlalchemy import select, and_
    from src.models.user import User
    
    query = select(User).where(
        and_(
            User.role == UserRole.PERWADAG,
            User.is_active == True,
            User.deleted_at.is_(None)
        )
    ).order_by(User.nama)
    
    result = await session.execute(query)
    perwadag_list = result.scalars().all()
    
    # Format response
    available_perwadag = []
    for perwadag in perwadag_list:
        available_perwadag.append({
            "id": perwadag.id,
            "nama": perwadag.nama,
            "inspektorat": perwadag.inspektorat,
            "email": perwadag.email,
            "has_email": perwadag.has_email()
        })
    
    return {
        "available_perwadag": available_perwadag,
        "total": len(available_perwadag)
    }


# ===== BULK OPERATIONS =====

# @router.post("/bulk/progress-check")
# async def bulk_check_progress(
#     surat_tugas_ids: list[str],
#     current_user: dict = Depends(require_evaluasi_read_access()),
#     surat_tugas_service: SuratTugasService = Depends(get_surat_tugas_service)
# ):
#     """
#     Bulk check progress untuk multiple surat tugas.
    
#     **Use case**: Dashboard overview, progress monitoring
    
#     **Returns**: Progress data untuk setiap surat tugas ID
#     """
#     progress_data = []
    
#     for surat_tugas_id in surat_tugas_ids:
#         try:
#             surat_tugas = await surat_tugas_service.get_surat_tugas_or_404(surat_tugas_id)
#             progress_data.append({
#                 "surat_tugas_id": surat_tugas_id,
#                 "no_surat": surat_tugas.no_surat,
#                 "nama_perwadag": surat_tugas.nama_perwadag,
#                 "progress": surat_tugas.progress,
#                 "evaluation_status": surat_tugas.evaluation_status
#             })
#         except HTTPException:
#             progress_data.append({
#                 "surat_tugas_id": surat_tugas_id,
#                 "error": "Surat tugas not found or access denied"
#             })
    
#     return {
#         "progress_data": progress_data,
#         "total_checked": len(surat_tugas_ids),
#         "successful": len([p for p in progress_data if "error" not in p])
#     }


# ===== DASHBOARD ENDPOINTS =====

@router.get("/dashboard/summary")
async def get_dashboard_summary(
    current_user: dict = Depends(require_evaluasi_read_access()),
    surat_tugas_service: SuratTugasService = Depends(get_surat_tugas_service)
):
    """
    Get dashboard summary untuk current user.
    
    **Role-based Summary**:
    - **Admin**: Summary semua evaluasi
    - **Inspektorat**: Summary wilayah kerja
    - **Perwadag**: Summary evaluasi milik sendiri
    
    **Returns**:
    - Quick stats
    - Recent surat tugas
    - Progress overview
    - Pending actions
    """
    filter_scope = get_evaluasi_filter_scope(current_user)
    
    # Get statistics
    stats = await surat_tugas_service.get_statistics(
        filter_scope["user_role"],
        filter_scope.get("user_inspektorat"),
        filter_scope.get("user_id")
    )
    
    # Get recent surat tugas (last 5)
    from src.schemas.filters import SuratTugasFilterParams
    recent_filters = SuratTugasFilterParams(page=1, size=5)
    
    recent_surat_tugas = await surat_tugas_service.get_all_surat_tugas(
        recent_filters,
        filter_scope["user_role"],
        filter_scope.get("user_inspektorat"),
        filter_scope.get("user_id")
    )
    
    return {
        "user_info": {
            "nama": current_user["nama"],
            "role": current_user["role"],
            "inspektorat": current_user.get("inspektorat")
        },
        "statistics": stats,
        "recent_surat_tugas": recent_surat_tugas.surat_tugas,
        "quick_actions": {
            "can_create_surat_tugas": current_user["role"] in ["ADMIN", "INSPEKTORAT"],
            "can_manage_templates": current_user["role"] == "ADMIN",
            "total_evaluasi": stats.total_surat_tugas
        }
    }