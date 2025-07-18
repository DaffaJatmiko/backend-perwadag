# ===== src/api/endpoints/periode_evaluasi.py =====
"""API endpoints untuk periode evaluasi."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.repositories.periode_evaluasi import PeriodeEvaluasiRepository
from src.repositories.penilaian_risiko import PenilaianRisikoRepository
from src.services.periode_evaluasi import PeriodeEvaluasiService
from src.schemas.periode_evaluasi import (
    PeriodeEvaluasiCreate, PeriodeEvaluasiUpdate, PeriodeEvaluasiResponse,
    PeriodeEvaluasiListResponse, PeriodeEvaluasiCreateResponse
)
from src.schemas.filters import PeriodeEvaluasiFilterParams
from src.schemas.common import SuccessResponse
from src.auth.permissions import get_current_active_user, require_roles

router = APIRouter()

# Permission dependencies
admin_required = require_roles(["ADMIN"])
admin_or_inspektorat = require_roles(["ADMIN", "INSPEKTORAT"])


async def get_periode_evaluasi_service(session: AsyncSession = Depends(get_db)) -> PeriodeEvaluasiService:
    """Dependency untuk PeriodeEvaluasiService."""
    periode_repo = PeriodeEvaluasiRepository(session)
    penilaian_repo = PenilaianRisikoRepository(session)
    return PeriodeEvaluasiService(periode_repo, penilaian_repo)


# ===== CREATE OPERATIONS =====

@router.post("/", response_model=PeriodeEvaluasiCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_periode_evaluasi(
    periode_data: PeriodeEvaluasiCreate,
    current_user: dict = Depends(admin_required),
    periode_service: PeriodeEvaluasiService = Depends(get_periode_evaluasi_service)
):
    """
    Create periode evaluasi baru dengan AUTO BULK GENERATE penilaian risiko.
    
    **Accessible by**: Admin only
    
    **Auto Bulk Generate Process**:
    1. Create periode evaluasi
    2. AUTO-GENERATE penilaian risiko untuk semua perwadag aktif
    3. Generate kriteria_data template dengan tahun_pembanding otomatis
    
    **Business Rules**:
    - Tahun harus unique (tidak boleh duplikat)
    - Tahun minimal 2020
    - Sistem otomatis generate tahun_pembanding_1 = tahun-2, tahun_pembanding_2 = tahun-1
    
    **Returns**: Periode evaluasi data + summary hasil bulk generate
    
    **Example**:
    - Input tahun: 2025
    - Auto generate untuk tahun_pembanding_1: 2023, tahun_pembanding_2: 2024
    - Bulk create penilaian risiko untuk semua perwadag aktif
    """
    return await periode_service.create_periode_with_bulk_generate(
        periode_data, current_user["id"]
    )


# ===== READ OPERATIONS =====

@router.get("/", response_model=PeriodeEvaluasiListResponse)
async def get_all_periode_evaluasi(
    filters: PeriodeEvaluasiFilterParams = Depends(),
    current_user: dict = Depends(admin_or_inspektorat),
    periode_service: PeriodeEvaluasiService = Depends(get_periode_evaluasi_service)
):
    """
    Get all periode evaluasi dengan filtering.
    
    **Accessible by**: Admin dan Inspektorat
    
    **Query Parameters**:
    - page, size: Pagination
    - search: Search by tahun
    - is_locked: Filter by lock status
    - tahun_from, tahun_to: Filter range tahun
    - include_statistics: Include statistics dalam response
    
    **Returns**: Paginated list dengan statistics per periode
    """
    return await periode_service.get_all_periode_evaluasi(filters)


@router.get("/{periode_id}", response_model=PeriodeEvaluasiResponse)
async def get_periode_evaluasi(
    periode_id: str,
    current_user: dict = Depends(admin_or_inspektorat),
    periode_service: PeriodeEvaluasiService = Depends(get_periode_evaluasi_service)
):
    """
    Get periode evaluasi by ID.
    
    **Accessible by**: Admin dan Inspektorat
    
    **Returns**: Complete periode data dengan computed fields
    """
    return await periode_service.get_periode_or_404(periode_id)


# ===== UPDATE OPERATIONS =====

@router.put("/{periode_id}", response_model=PeriodeEvaluasiResponse)
async def update_periode_evaluasi(
    periode_id: str,
    periode_data: PeriodeEvaluasiUpdate,
    current_user: dict = Depends(admin_required),
    periode_service: PeriodeEvaluasiService = Depends(get_periode_evaluasi_service)
):
    """
    Update periode evaluasi (lock/unlock, status).
    
    **Accessible by**: Admin only
    
    **Updatable fields**:
    - is_locked: Lock/unlock periode untuk editing
    
    **Business Rules**:
    - Hanya admin yang bisa lock/unlock periode
    - Periode yang locked tidak bisa diedit penilaian risikonya
    - Status tutup mencegah editing
    """
    return await periode_service.update_periode_evaluasi(
        periode_id, periode_data, current_user["id"]
    )


# ===== DELETE OPERATIONS =====

@router.delete("/{periode_id}", response_model=SuccessResponse)
async def delete_periode_evaluasi(
    periode_id: str,
    current_user: dict = Depends(admin_required),
    periode_service: PeriodeEvaluasiService = Depends(get_periode_evaluasi_service)
):
    """
    Delete periode evaluasi dengan CASCADE DELETE penilaian risiko.
    
    **Accessible by**: Admin only
    
    **CASCADE DELETE Process**:
    1. Delete semua penilaian_risiko yang terkait dengan periode_id
    2. Delete periode_evaluasi
    
    **Warning**: This is HARD DELETE and cannot be undone!
    
    **Why Cascade Delete**:
    - Data penilaian risiko tidak bermakna tanpa periode
    - Menghindari orphaned data
    - Menjaga konsistensi database
    """
    return await periode_service.delete_periode_evaluasi(periode_id, current_user["id"])


# ===== UTILITY ENDPOINTS =====

@router.get("/check/tahun-availability")
async def check_tahun_availability(
    tahun: int,
    current_user: dict = Depends(admin_required),
    session: AsyncSession = Depends(get_db)
):
    """
    Check availability tahun periode.
    
    **Use case**: Validation saat create periode evaluasi
    
    **Returns**: 
    - available: true/false
    - message: explanation
    - tahun_pembanding: preview tahun yang akan digunakan
    """
    periode_repo = PeriodeEvaluasiRepository(session)
    
    exists = await periode_repo.tahun_exists(tahun)
    
    # Generate preview tahun pembanding
    tahun_pembanding = {
        "tahun_pembanding_1": tahun - 2,
        "tahun_pembanding_2": tahun - 1
    }
    
    return {
        "tahun": tahun,
        "available": not exists,
        "message": "Tahun periode available" if not exists else "Tahun periode sudah ada",
        "tahun_pembanding": tahun_pembanding
    }


@router.get("/statistics/overview")
async def get_periode_statistics(
    current_user: dict = Depends(admin_required),
    periode_service: PeriodeEvaluasiService = Depends(get_periode_evaluasi_service)
):
    """
    Get comprehensive statistics periode evaluasi.
    
    **Accessible by**: Admin only
    
    **Returns**:
    - Total periode
    - Breakdown by status (aktif/tutup)
    - Breakdown by lock status
    - Summary completion rates
    """
    return await periode_service.get_statistics()
