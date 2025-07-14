# ===== src/api/endpoints/matriks.py =====
"""API endpoints untuk matriks."""

from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.repositories.matriks import MatriksRepository
from src.services.matriks import MatriksService
from src.schemas.matriks import MatriksResponse, MatriksFileUploadResponse
from src.auth.evaluasi_permissions import (
    require_evaluasi_read_access, require_auto_generated_edit_access
)

router = APIRouter()


async def get_matriks_service(session: AsyncSession = Depends(get_db)) -> MatriksService:
    """Dependency untuk MatriksService."""
    matriks_repo = MatriksRepository(session)
    return MatriksService(matriks_repo)


@router.get("/{matriks_id}", response_model=MatriksResponse)
async def get_matriks(
    matriks_id: str,
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: MatriksService = Depends(get_matriks_service)
):
    """Get matriks by ID."""
    return await service.get_matriks_or_404(matriks_id)


@router.get("/surat-tugas/{surat_tugas_id}", response_model=MatriksResponse)
async def get_matriks_by_surat_tugas(
    surat_tugas_id: str,
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: MatriksService = Depends(get_matriks_service)
):
    """Get matriks by surat tugas ID."""
    result = await service.get_by_surat_tugas_id(surat_tugas_id)
    if not result:
        raise HTTPException(status_code=404, detail="Matriks not found")
    return result


@router.post("/{matriks_id}/upload-file", response_model=MatriksFileUploadResponse)
async def upload_matriks_file(
    matriks_id: str,
    file: UploadFile = File(..., description="File matriks rekomendasi"),
    current_user: dict = Depends(require_auto_generated_edit_access()),
    service: MatriksService = Depends(get_matriks_service)
):
    """Upload file matriks rekomendasi."""
    return await service.upload_file(matriks_id, file, current_user["id"])

