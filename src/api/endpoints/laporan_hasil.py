# ===== src/api/endpoints/laporan_hasil.py =====
"""API endpoints untuk laporan hasil."""

from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.repositories.laporan_hasil import LaporanHasilRepository
from src.services.laporan_hasil import LaporanHasilService
from src.schemas.laporan_hasil import (
    LaporanHasilUpdate, LaporanHasilResponse, LaporanHasilFileUploadResponse
)
from src.auth.evaluasi_permissions import (
    require_evaluasi_read_access, require_laporan_edit_access
)

router = APIRouter()


async def get_laporan_hasil_service(session: AsyncSession = Depends(get_db)) -> LaporanHasilService:
    """Dependency untuk LaporanHasilService."""
    laporan_hasil_repo = LaporanHasilRepository(session)
    return LaporanHasilService(laporan_hasil_repo)


@router.get("/{laporan_hasil_id}", response_model=LaporanHasilResponse)
async def get_laporan_hasil(
    laporan_hasil_id: str,
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: LaporanHasilService = Depends(get_laporan_hasil_service)
):
    """Get laporan hasil by ID."""
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
    current_user: dict = Depends(require_laporan_edit_access()),
    service: LaporanHasilService = Depends(get_laporan_hasil_service)
):
    """
    Update laporan hasil - PERWADAG dapat full edit.
    
    **Accessible by**: Admin, Inspektorat, Perwadag (milik sendiri)
    **Updatable**: nomor_laporan, tanggal_laporan
    """
    return await service.update_laporan_hasil(laporan_hasil_id, update_data, current_user["id"])


@router.post("/{laporan_hasil_id}/upload-file", response_model=LaporanHasilFileUploadResponse)
async def upload_laporan_hasil_file(
    laporan_hasil_id: str,
    file: UploadFile = File(..., description="File laporan hasil"),
    current_user: dict = Depends(require_laporan_edit_access()),
    service: LaporanHasilService = Depends(get_laporan_hasil_service)
):
    """Upload file laporan hasil - PERWADAG dapat upload."""
    return await service.upload_file(laporan_hasil_id, file, current_user["id"])

