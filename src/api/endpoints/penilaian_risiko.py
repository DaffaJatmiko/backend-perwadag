# ===== src/api/endpoints/penilaian_risiko.py =====
"""API endpoints untuk penilaian risiko."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.repositories.penilaian_risiko import PenilaianRisikoRepository
from src.repositories.periode_evaluasi import PeriodeEvaluasiRepository
from src.repositories.user import UserRepository
from src.services.penilaian_risiko import PenilaianRisikoService
from src.schemas.penilaian_risiko import (
    PenilaianRisikoUpdate, PenilaianRisikoResponse, PenilaianRisikoListResponse,
    PenilaianRisikoCalculateRequest, PenilaianRisikoCalculateResponse,
    KriteriaOptionsResponse
)
from src.schemas.filters import PenilaianRisikoFilterParams
from src.auth.permissions import get_current_active_user, require_roles

router = APIRouter()

# Permission dependencies
admin_required = require_roles(["ADMIN"])
admin_or_inspektorat = require_roles(["ADMIN", "INSPEKTORAT"])


async def get_penilaian_risiko_service(session: AsyncSession = Depends(get_db)) -> PenilaianRisikoService:
    """Dependency untuk PenilaianRisikoService."""
    penilaian_repo = PenilaianRisikoRepository(session)
    periode_repo = PeriodeEvaluasiRepository(session)
    user_repo = UserRepository(session)
    return PenilaianRisikoService(penilaian_repo, periode_repo, user_repo)


def get_evaluasi_filter_scope(current_user: dict) -> dict:
    """Get filter scope berdasarkan role user."""
    user_role = current_user.get("role")
    
    if user_role == "ADMIN":
        return {
            "user_role": user_role,
            "user_inspektorat": None,
            "user_id": None
        }
    elif user_role == "INSPEKTORAT":
        return {
            "user_role": user_role,
            "user_inspektorat": current_user.get("inspektorat"),
            "user_id": current_user.get("id")
        }
    else:
        # Default fallback
        return {
            "user_role": user_role,
            "user_inspektorat": None,
            "user_id": current_user.get("id")
        }


# ===== READ OPERATIONS =====

@router.get("/", response_model=PenilaianRisikoListResponse)
async def get_all_penilaian_risiko(
    filters: PenilaianRisikoFilterParams = Depends(),
    current_user: dict = Depends(admin_or_inspektorat),
    penilaian_service: PenilaianRisikoService = Depends(get_penilaian_risiko_service)
):
    """
    Get all penilaian risiko dengan comprehensive filtering.
    
    **Accessible by**: Admin dan Inspektorat dengan scope filtering:
    - **Admin**: Lihat semua penilaian risiko
    - **Inspektorat**: Lihat penilaian risiko di wilayah kerjanya only
    
    **Query Parameters**:
    - page, size: Pagination
    - search: Search dalam nama perwadag, inspektorat
    - periode_id: Filter by periode
    - user_perwadag_id: Filter by perwadag
    - inspektorat: Filter by inspektorat
    - tahun: Filter by tahun
    - is_complete: Filter data yang lengkap (true/false)
    - sort_by: Urutan data (skor_tertinggi, skor_terendah, nama, created_at)
    
    **Sorting Options**:
    - skor_tertinggi: Urutkan dari skor rata-rata tertinggi
    - skor_terendah: Urutkan dari skor rata-rata terendah  
    - nama: Urutkan berdasarkan nama perwadag A-Z
    - created_at: Urutkan berdasarkan tanggal dibuat (default)
    
    **Examples**:
    - `GET /penilaian-risiko?sort_by=skor_tertinggi` - Lihat yang skor tertinggi dulu
    - `GET /penilaian-risiko?periode_id=xxx&sort_by=skor_terendah` - Periode tertentu, skor terendah dulu
    - `GET /penilaian-risiko?is_complete=true&sort_by=nama` - Yang sudah lengkap, urutkan nama
    
    **Returns**: Paginated list dengan enriched data dan sorting
    """
    filter_scope = get_evaluasi_filter_scope(current_user)
    
    return await penilaian_service.get_all_penilaian_risiko(
        filters,
        filter_scope["user_role"],
        filter_scope["user_inspektorat"],
        filter_scope["user_id"]
    )


@router.get("/{penilaian_id}", response_model=PenilaianRisikoResponse)
async def get_penilaian_risiko(
    penilaian_id: str,
    current_user: dict = Depends(admin_or_inspektorat),
    penilaian_service: PenilaianRisikoService = Depends(get_penilaian_risiko_service)
):
    """
    Get penilaian risiko by ID.
    
    **Access Control**: Role-based dengan validation di service layer
    
    **Returns**: Complete penilaian data dengan kriteria dan hasil kalkulasi
    """
    return await penilaian_service.get_penilaian_or_404(penilaian_id)


# ===== UPDATE OPERATIONS =====

@router.put("/{penilaian_id}", response_model=PenilaianRisikoResponse)
async def update_penilaian_risiko(
    penilaian_id: str,
    penilaian_data: PenilaianRisikoUpdate,
    current_user: dict = Depends(admin_or_inspektorat),
    penilaian_service: PenilaianRisikoService = Depends(get_penilaian_risiko_service)
):
    """
    Update penilaian risiko dengan AUTO-CALCULATE functionality.
    
    **🚀 ONE-STEP PROCESS**: Input data + Auto Calculate dalam 1 endpoint!
    
    **Auto-Calculate Logic**:
    - Jika `auto_calculate: true` (default) dan data kriteria lengkap
    - Sistem otomatis calculate total_nilai_risiko & profil_risiko
    - User tidak perlu hit endpoint calculate terpisah
    
    **Request Body**:
    ```json
    {
      "kriteria_data": { ... },
      "catatan": "Optional notes",
      "auto_calculate": true  // default true
    }
    ```
    
    **Response Enhancement**:
    - `calculation_performed`: true jika auto-calculate berhasil
    - `calculation_details`: detail hasil kalkulasi
    - `profil_risiko_auditan`: hasil final (Rendah/Sedang/Tinggi)
    
    **User Experience**:
    1. User input semua data kriteria
    2. Click SAVE → langsung dapat hasil kalkulasi
    3. Tidak perlu step tambahan!
    
    **Manual Calculate (Optional)**:
    - Set `auto_calculate: false` jika hanya mau save data
    - Hit `/calculate` endpoint nanti jika diperlukan
    """
    filter_scope = get_evaluasi_filter_scope(current_user)
    
    return await penilaian_service.update_penilaian_risiko(
        penilaian_id,
        penilaian_data,
        current_user["id"],
        filter_scope["user_role"],
        filter_scope["user_inspektorat"]
    )


# @router.post("/{penilaian_id}/calculate", response_model=PenilaianRisikoCalculateResponse)
# async def calculate_penilaian_risiko(
#     penilaian_id: str,
#     calculate_request: PenilaianRisikoCalculateRequest,
#     current_user: dict = Depends(admin_or_inspektorat),
#     penilaian_service: PenilaianRisikoService = Depends(get_penilaian_risiko_service)
# ):
#     """
#     Kalkulasi total nilai risiko dan profil risiko auditan.
    
#     **Accessible by**: Admin dan Inspektorat (dengan access validation)
    
#     **Requirements**:
#     - Semua 8 kriteria harus memiliki nilai (tidak null)
#     - Periode masih editable
#     - User punya akses ke penilaian
    
#     **Calculation Formula**:
#     ```
#     total_nilai_risiko = (
#         (nilai1 * 15) + (nilai2 * 10) + (nilai3 * 15) + (nilai4 * 25) + 
#         (nilai5 * 5) + (nilai6 * 10) + (nilai7 * 10) + (nilai8 * 10)
#     ) / 5
    
#     skor_rata_rata = (nilai1 + nilai2 + ... + nilai8) / 8
    
#     profil_risiko_auditan:
#     - skor_rata_rata <= 2.0 → "Rendah"
#     - skor_rata_rata <= 3.5 → "Sedang"  
#     - skor_rata_rata > 3.5 → "Tinggi"
#     ```
    
#     **Parameters**:
#     - force_recalculate: Recalculate meskipun sudah ada hasil sebelumnya
    
#     **Returns**: Updated penilaian dengan hasil kalkulasi + calculation details
#     """
#     filter_scope = get_evaluasi_filter_scope(current_user)
    
#     return await penilaian_service.calculate_penilaian_risiko(
#         penilaian_id,
#         calculate_request,
#         current_user["id"],
#         filter_scope["user_role"],
#         filter_scope["user_inspektorat"]
#     )


# ===== UTILITY ENDPOINTS =====

# @router.get("/options/kriteria", response_model=KriteriaOptionsResponse)
# async def get_kriteria_options(
#     current_user: dict = Depends(admin_or_inspektorat),
#     penilaian_service: PenilaianRisikoService = Depends(get_penilaian_risiko_service)
# ):
#     """
#     Get opsi-opsi untuk dropdown kriteria penilaian.
    
#     **Returns**:
#     - audit_itjen_options: 1 Tahun, 2 Tahun, ..., Belum pernah diaudit
#     - perjanjian_perdagangan_options: Tidak ada perjanjian, Sedang diusulkan, ...
    
#     **Use case**: Populate dropdown options di frontend
#     """
#     return await penilaian_service.get_kriteria_options()


# @router.get("/statistics/overview")
# async def get_penilaian_statistics(
#     current_user: dict = Depends(admin_or_inspektorat),
#     penilaian_service: PenilaianRisikoService = Depends(get_penilaian_risiko_service)
# ):
#     """
#     Get comprehensive statistics penilaian risiko.
    
#     **Role-based Statistics**:
#     - **Admin**: Statistics semua penilaian risiko
#     - **Inspektorat**: Statistics untuk wilayah kerjanya
    
#     **Returns**:
#     - Total penilaian dan completion rate
#     - Breakdown by profil risiko (Rendah/Sedang/Tinggi)
#     - Breakdown by inspektorat (admin only)
#     - Average scores
#     """
#     filter_scope = get_evaluasi_filter_scope(current_user)
    
#     return await penilaian_service.get_statistics(
#         filter_scope["user_role"],
#         filter_scope["user_inspektorat"],
#         filter_scope["user_id"]
#     )


@router.get("/periode/{periode_id}/summary")
async def get_periode_penilaian_summary(
    periode_id: str,
    current_user: dict = Depends(admin_or_inspektorat),
    penilaian_service: PenilaianRisikoService = Depends(get_penilaian_risiko_service)
):
    """
    Get summary penilaian risiko untuk periode tertentu.
    
    **Use case**: Dashboard periode-specific
    
    **Returns**: Statistics dan summary untuk periode yang dipilih
    """
    from src.schemas.filters_penilaian import PenilaianRisikoFilterParams
    
    filter_scope = get_evaluasi_filter_scope(current_user)
    
    # Filter by periode
    filters = PenilaianRisikoFilterParams(
        periode_id=periode_id,
        include_statistics=True,
        page=1,
        size=1000  # Get all untuk summary
    )
    
    result = await penilaian_service.get_all_penilaian_risiko(
        filters,
        filter_scope["user_role"],
        filter_scope["user_inspektorat"],
        filter_scope["user_id"]
    )
    
    return {
        "periode_id": periode_id,
        "total_penilaian": result.pagination.total,
        "statistics": result.statistics,
        "summary": {
            "completion_rate": result.statistics.get("completion_rate", 0) if result.statistics else 0,
            "profil_breakdown": {
                "rendah": result.statistics.get("profil_rendah", 0) if result.statistics else 0,
                "sedang": result.statistics.get("profil_sedang", 0) if result.statistics else 0,
                "tinggi": result.statistics.get("profil_tinggi", 0) if result.statistics else 0
            }
        }
    }


# ===== BULK OPERATIONS =====

# @router.post("/bulk/calculate")
# async def bulk_calculate_by_periode(
#     periode_id: str,
#     force_recalculate: bool = False,
#     current_user: dict = Depends(admin_required),
#     penilaian_service: PenilaianRisikoService = Depends(get_penilaian_risiko_service)
# ):
#     """
#     Bulk calculate semua penilaian risiko dalam periode tertentu.
    
#     **Accessible by**: Admin only
    
#     **Use case**: Kalkulasi massal untuk periode yang sudah lengkap datanya
    
#     **Parameters**:
#     - periode_id: ID periode yang akan dikalkulasi
#     - force_recalculate: Recalculate yang sudah ada hasil
    
#     **Returns**: Summary hasil bulk calculation
#     """
#     from src.schemas.filters_penilaian import PenilaianRisikoFilterParams
    
#     # Get all penilaian in periode
#     filters = PenilaianRisikoFilterParams(
#         periode_id=periode_id,
#         page=1,
#         size=1000  # Get all
#     )
    
#     result = await penilaian_service.get_all_penilaian_risiko(
#         filters, "ADMIN", None, None
#     )
    
#     # Process each penilaian
#     success_count = 0
#     failed_count = 0
#     skipped_count = 0
#     errors = []
    
#     for penilaian in result.penilaian_risiko:
#         try:
#             # Skip if already calculated and not forced
#             if penilaian.has_calculation_result and not force_recalculate:
#                 skipped_count += 1
#                 continue
            
#             # Skip if data not complete
#             if not penilaian.is_calculation_complete:
#                 failed_count += 1
#                 errors.append({
#                     "penilaian_id": penilaian.id,
#                     "perwadag": penilaian.nama_perwadag,
#                     "error": "Data kriteria tidak lengkap"
#                 })
#                 continue
            
#             # Calculate
#             calculate_request = PenilaianRisikoCalculateRequest(force_recalculate=force_recalculate)
#             await penilaian_service.calculate_penilaian_risiko(
#                 penilaian.id,
#                 calculate_request,
#                 current_user["id"],
#                 "ADMIN",
#                 None
#             )
#             success_count += 1
            
#         except Exception as e:
#             failed_count += 1
#             errors.append({
#                 "penilaian_id": penilaian.id,
#                 "perwadag": penilaian.nama_perwadag,
#                 "error": str(e)
#             })
    
#     return {
#         "success": True,
#         "message": f"Bulk calculation completed: {success_count} success, {failed_count} failed, {skipped_count} skipped",
#         "periode_id": periode_id,
#         "total_processed": success_count + failed_count + skipped_count,
#         "success_count": success_count,
#         "failed_count": failed_count,
#         "skipped_count": skipped_count,
#         "errors": errors[:10]  # Limit error details
#     }
