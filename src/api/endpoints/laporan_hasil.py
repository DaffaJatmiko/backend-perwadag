# ===== src/api/endpoints/laporan_hasil.py =====
"""Enhanced API endpoints untuk laporan hasil evaluasi."""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Path
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.repositories.laporan_hasil import LaporanHasilRepository
from src.services.laporan_hasil import LaporanHasilService
from src.schemas.laporan_hasil import (
    LaporanHasilUpdate, LaporanHasilResponse,
    LaporanHasilFileUploadResponse, LaporanHasilListResponse
)
from src.schemas.filters import LaporanHasilFilterParams
from src.auth.evaluasi_permissions import (
    require_evaluasi_read_access, require_auto_generated_edit_access, get_evaluasi_filter_scope
)
from src.schemas.shared import FileDeleteResponse


router = APIRouter()


async def get_laporan_hasil_service(session: AsyncSession = Depends(get_db)) -> LaporanHasilService:
    """Dependency untuk LaporanHasilService."""
    laporan_hasil_repo = LaporanHasilRepository(session)
    return LaporanHasilService(laporan_hasil_repo)


@router.get("/", response_model=LaporanHasilListResponse)
async def get_all_laporan_hasil(
    filters: LaporanHasilFilterParams = Depends(),
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: LaporanHasilService = Depends(get_laporan_hasil_service)
):
    """
    Get all laporan hasil dengan comprehensive filtering dan enriched data.
    
    **Role-based Access:**
    - **Admin**: Semua data laporan hasil
    - **Inspektorat**: Data di wilayah kerjanya
    - **Perwadag**: Data milik sendiri only
    
    **Enhanced Features:**
    - Include tanggal evaluasi, nama perwadag, inspektorat dari surat tugas
    - File download/view URLs
    - Completion statistics
    - Advanced filtering options
    """
    filter_scope = get_evaluasi_filter_scope(current_user)
      
    return await service.get_all_laporan_hasil(
        filters=filters,
        user_role=filter_scope["user_role"],
        user_inspektorat=filter_scope.get("user_inspektorat"),
        user_id=filter_scope.get("user_id")
    )


@router.get("/{laporan_hasil_id}", response_model=LaporanHasilResponse)
async def get_laporan_hasil(
    laporan_hasil_id: str,
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: LaporanHasilService = Depends(get_laporan_hasil_service)
):
    """Get laporan hasil by ID dengan enriched data."""
    return await service.get_laporan_hasil_or_404(laporan_hasil_id)


@router.get("/surat-tugas/{surat_tugas_id}", response_model=LaporanHasilResponse)
async def get_laporan_hasil_by_surat_tugas(
    surat_tugas_id: str,
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: LaporanHasilService = Depends(get_laporan_hasil_service)
):
    """Get laporan hasil by surat tugas ID."""
    result = await service.get_by_surat_tugas_id(surat_tugas_id)
    if not result:
        raise HTTPException(status_code=404, detail="Laporan hasil not found")
    return result


@router.put("/{laporan_hasil_id}", response_model=LaporanHasilResponse)
async def update_laporan_hasil(
    laporan_hasil_id: str,
    update_data: LaporanHasilUpdate,
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: LaporanHasilService = Depends(get_laporan_hasil_service)
):
    """Update laporan hasil (nomor laporan)."""
    return await service.update_laporan_hasil(laporan_hasil_id, update_data, current_user["id"])


@router.post("/{laporan_hasil_id}/upload-file", response_model=LaporanHasilFileUploadResponse)
async def upload_laporan_hasil_file(
    laporan_hasil_id: str,
    file: UploadFile = File(..., description="File laporan hasil"),
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: LaporanHasilService = Depends(get_laporan_hasil_service)
):
    """Upload file laporan hasil."""
    return await service.upload_file(laporan_hasil_id, file, current_user["id"])


@router.get("/{laporan_hasil_id}/download", response_class=FileResponse)
async def download_laporan_hasil_file(
    laporan_hasil_id: str = Path(..., description="Laporan Hasil ID"),
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: LaporanHasilService = Depends(get_laporan_hasil_service)
):
    """Download laporan hasil file."""
    return await service.download_file(laporan_hasil_id, download_type="download")

@router.delete("/{laporan_hasil_id}/files/{filename}", response_model=FileDeleteResponse)
async def delete_laporan_hasil_file(
    laporan_hasil_id: str,
    filename: str = Path(..., description="Filename to delete"),
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: LaporanHasilService = Depends(get_laporan_hasil_service)
):
    """
    Delete laporan hasil file by filename.
    
    **Accessible by**: Admin, Inspektorat, dan Perwadag (own data only)
    
    **Date Validation**: Cannot delete after evaluation period ends
    
    **Parameters**:
    - laporan_hasil_id: ID laporan hasil
    - filename: Nama file yang akan dihapus (harus exact match)
    """
    return await service.delete_file_by_filename(
        laporan_hasil_id, filename, current_user["id"], current_user
    )

@router.get("/{laporan_hasil_id}/view", response_class=FileResponse)
async def view_laporan_hasil_file(
    laporan_hasil_id: str = Path(..., description="Laporan Hasil ID"),
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: LaporanHasilService = Depends(get_laporan_hasil_service)
):
    """View/preview laporan hasil file in browser."""
    return await service.download_file(laporan_hasil_id, download_type="view")