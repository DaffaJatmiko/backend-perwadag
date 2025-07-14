# ===== src/api/endpoints/surat_pemberitahuan.py =====
"""API endpoints untuk surat pemberitahuan."""

from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.repositories.surat_pemberitahuan import SuratPemberitahuanRepository
from src.services.surat_pemberitahuan import SuratPemberitahuanService
from src.schemas.surat_pemberitahuan import (
    SuratPemberitahuanUpdate, SuratPemberitahuanResponse,
    SuratPemberitahuanFileUploadResponse
)
from src.auth.evaluasi_permissions import (
    require_evaluasi_read_access, require_auto_generated_edit_access
)

router = APIRouter()


async def get_surat_pemberitahuan_service(session: AsyncSession = Depends(get_db)) -> SuratPemberitahuanService:
    """Dependency untuk SuratPemberitahuanService."""
    surat_pemberitahuan_repo = SuratPemberitahuanRepository(session)
    return SuratPemberitahuanService(surat_pemberitahuan_repo)


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

