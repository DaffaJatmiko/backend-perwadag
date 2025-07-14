# ===== src/api/endpoints/kuisioner.py =====
"""API endpoints untuk kuisioner."""

from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.repositories.kuisioner import KuisionerRepository
from src.services.kuisioner import KuisionerService
from src.schemas.kuisioner import KuisionerResponse, KuisionerFileUploadResponse
from src.auth.evaluasi_permissions import (
    require_evaluasi_read_access, require_kuisioner_upload_access
)

router = APIRouter()


async def get_kuisioner_service(session: AsyncSession = Depends(get_db)) -> KuisionerService:
    """Dependency untuk KuisionerService."""
    kuisioner_repo = KuisionerRepository(session)
    return KuisionerService(kuisioner_repo)


@router.get("/{kuisioner_id}", response_model=KuisionerResponse)
async def get_kuisioner(
    kuisioner_id: str,
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: KuisionerService = Depends(get_kuisioner_service)
):
    """Get kuisioner by ID."""
    return await service.get_kuisioner_or_404(kuisioner_id)


@router.get("/surat-tugas/{surat_tugas_id}", response_model=KuisionerResponse)
async def get_kuisioner_by_surat_tugas(
    surat_tugas_id: str,
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: KuisionerService = Depends(get_kuisioner_service)
):
    """Get kuisioner by surat tugas ID."""
    result = await service.get_by_surat_tugas_id(surat_tugas_id)
    if not result:
        raise HTTPException(status_code=404, detail="Kuisioner not found")
    return result


@router.post("/{kuisioner_id}/upload-file", response_model=KuisionerFileUploadResponse)
async def upload_kuisioner_file(
    kuisioner_id: str,
    file: UploadFile = File(..., description="File kuisioner yang diisi"),
    current_user: dict = Depends(require_kuisioner_upload_access()),
    service: KuisionerService = Depends(get_kuisioner_service)
):
    """
    Upload file kuisioner - PERWADAG dapat upload.
    
    **Accessible by**: Admin, Inspektorat, Perwadag (milik sendiri)
    **File Types**: PDF, DOC, DOCX, XLS, XLSX
    """
    return await service.upload_file(kuisioner_id, file, current_user["id"])

