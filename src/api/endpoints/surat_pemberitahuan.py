# ===== src/api/endpoints/surat_pemberitahuan.py =====
"""API endpoints untuk surat pemberitahuan."""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Path
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.repositories.surat_pemberitahuan import SuratPemberitahuanRepository
from src.services.surat_pemberitahuan import SuratPemberitahuanService
from src.schemas.surat_pemberitahuan import (
    SuratPemberitahuanUpdate, SuratPemberitahuanResponse,
    SuratPemberitahuanFileUploadResponse, SuratPemberitahuanListResponse
)
from src.schemas.filters import SuratPemberitahuanFilterParams
from src.auth.evaluasi_permissions import (
    require_evaluasi_read_access, require_auto_generated_edit_access, get_evaluasi_filter_scope
)

router = APIRouter()


async def get_surat_pemberitahuan_service(session: AsyncSession = Depends(get_db)) -> SuratPemberitahuanService:
    """Dependency untuk SuratPemberitahuanService."""
    surat_pemberitahuan_repo = SuratPemberitahuanRepository(session)
    return SuratPemberitahuanService(surat_pemberitahuan_repo)


@router.get("/", response_model=SuratPemberitahuanListResponse)
async def get_all_surat_pemberitahuan(
    filters: SuratPemberitahuanFilterParams = Depends(),
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: SuratPemberitahuanService = Depends(get_surat_pemberitahuan_service)
):
    """
    Get all surat pemberitahuan dengan comprehensive filtering dan enriched data.
    
    **Role-based Access:**
    - **Admin**: Semua data surat pemberitahuan
    - **Inspektorat**: Data di wilayah kerjanya
    - **Perwadag**: Data milik sendiri only
    
    **Enhanced Features:**
    - Include tanggal evaluasi, nama perwadag, inspektorat dari surat tugas
    - File download/view URLs
    - Completion statistics
    - Advanced filtering options
    
    **Query Parameters:**
    - **Basic**: page, size, search
    - **Surat Tugas Related**: inspektorat, user_perwadag_id, tahun_evaluasi
    - **Status**: has_file, has_date, is_completed
    - **Date Range**: tanggal_from, tanggal_to, created_from, created_to
    """
    filter_scope = get_evaluasi_filter_scope(current_user)
      
    return await service.get_all_surat_pemberitahuan(
        filters=filters,
        user_role=filter_scope["user_role"],
        user_inspektorat=filter_scope.get("user_inspektorat"),
        user_id=filter_scope.get("user_id")
    )


@router.get("/{surat_pemberitahuan_id}", response_model=SuratPemberitahuanResponse)
async def get_surat_pemberitahuan(
    surat_pemberitahuan_id: str,
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: SuratPemberitahuanService = Depends(get_surat_pemberitahuan_service)
):
    """Get surat pemberitahuan by ID."""
    return await service.get_surat_pemberitahuan_or_404(surat_pemberitahuan_id)


@router.get("/surat-tugas/{surat_tugas_id}", response_model=SuratPemberitahuanResponse)
async def get_surat_pemberitahuan_by_surat_tugas(
    surat_tugas_id: str,
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: SuratPemberitahuanService = Depends(get_surat_pemberitahuan_service)
):
    """Get surat pemberitahuan by surat tugas ID."""
    result = await service.get_by_surat_tugas_id(surat_tugas_id)
    if not result:
        raise HTTPException(status_code=404, detail="Surat pemberitahuan not found")
    return result


@router.put("/{surat_pemberitahuan_id}", response_model=SuratPemberitahuanResponse)
async def update_surat_pemberitahuan(
    surat_pemberitahuan_id: str,
    update_data: SuratPemberitahuanUpdate,
    current_user: dict = Depends(require_auto_generated_edit_access()),
    service: SuratPemberitahuanService = Depends(get_surat_pemberitahuan_service)
):
    """Update surat pemberitahuan (tanggal)."""
    return await service.update_surat_pemberitahuan(surat_pemberitahuan_id, update_data, current_user["id"])


@router.post("/{surat_pemberitahuan_id}/upload-file", response_model=SuratPemberitahuanFileUploadResponse)
async def upload_surat_pemberitahuan_file(
    surat_pemberitahuan_id: str,
    file: UploadFile = File(..., description="File surat pemberitahuan"),
    current_user: dict = Depends(require_auto_generated_edit_access()),
    service: SuratPemberitahuanService = Depends(get_surat_pemberitahuan_service)
):
    """Upload file surat pemberitahuan."""
    return await service.upload_file(surat_pemberitahuan_id, file, current_user["id"])


@router.get("/{surat_pemberitahuan_id}/download", response_class=FileResponse)
async def download_surat_pemberitahuan_file(
    surat_pemberitahuan_id: str = Path(..., description="Surat pemberitahuan ID"),
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: SuratPemberitahuanService = Depends(get_surat_pemberitahuan_service)
):
    """
    Download surat pemberitahuan file.
    
    **Response**: File download dengan proper headers
    **Access Control**: Role-based access dengan ownership validation
    """
    return await service.download_file(surat_pemberitahuan_id, download_type="download")

@router.get("/{surat_pemberitahuan_id}/view", response_class=FileResponse)
async def view_surat_pemberitahuan_file(
    surat_pemberitahuan_id: str = Path(..., description="Surat pemberitahuan ID"),
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: SuratPemberitahuanService = Depends(get_surat_pemberitahuan_service)
):
    """
    View/preview surat pemberitahuan file in browser.
    
    **Response**: File view dengan inline content disposition untuk PDF/images
    **Use Case**: Preview file tanpa download untuk supported file types
    """
    return await service.download_file(surat_pemberitahuan_id, download_type="view")