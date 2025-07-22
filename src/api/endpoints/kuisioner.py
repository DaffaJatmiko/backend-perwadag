# ===== src/api/endpoints/kuisioner.py =====
"""Enhanced API endpoints untuk kuisioner evaluasi."""

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Path
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.repositories.kuisioner import KuisionerRepository
from src.services.kuisioner import KuisionerService
from src.schemas.kuisioner import (
    KuisionerUpdate, KuisionerResponse,
    KuisionerFileUploadResponse, KuisionerListResponse
)
from src.schemas.filters import KuisionerFilterParams
from src.auth.evaluasi_permissions import (
    require_evaluasi_read_access, require_auto_generated_edit_access, get_evaluasi_filter_scope
)

router = APIRouter()


async def get_kuisioner_service(session: AsyncSession = Depends(get_db)) -> KuisionerService:
    """Dependency untuk KuisionerService."""
    kuisioner_repo = KuisionerRepository(session)
    return KuisionerService(kuisioner_repo)


@router.get("/", response_model=KuisionerListResponse)
async def get_all_kuisioner(
    filters: KuisionerFilterParams = Depends(),
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: KuisionerService = Depends(get_kuisioner_service)
):
    """
    Get all kuisioner dengan comprehensive filtering dan enriched data.
    
    **Role-based Access:**
    - **Admin**: Semua data kuisioner
    - **Inspektorat**: Data di wilayah kerjanya
    - **Perwadag**: Data milik sendiri only
    
    **Enhanced Features:**
    - Include tanggal evaluasi, nama perwadag, inspektorat dari surat tugas
    - File download/view URLs
    - Completion statistics
    - Advanced filtering options
    """
    filter_scope = get_evaluasi_filter_scope(current_user)
      
    return await service.get_all_kuisioner(
        filters=filters,
        user_role=filter_scope["user_role"],
        user_inspektorat=filter_scope.get("user_inspektorat"),
        user_id=filter_scope.get("user_id")
    )


@router.get("/{kuisioner_id}", response_model=KuisionerResponse)
async def get_kuisioner(
    kuisioner_id: str,
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: KuisionerService = Depends(get_kuisioner_service)
):
    """Get kuisioner by ID dengan enriched data."""
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


@router.put("/{kuisioner_id}", response_model=KuisionerResponse)
async def update_kuisioner(
    kuisioner_id: str,
    update_data: KuisionerUpdate,
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: KuisionerService = Depends(get_kuisioner_service)
):
    """Update kuisioner (nomor kuisioner)."""
    return await service.update_kuisioner(kuisioner_id, update_data, current_user["id"])


@router.post("/{kuisioner_id}/upload-file", response_model=KuisionerFileUploadResponse)
async def upload_kuisioner_file(
    kuisioner_id: str,
    file: UploadFile = File(..., description="File kuisioner"),
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: KuisionerService = Depends(get_kuisioner_service)
):
    """Upload file kuisioner."""
    return await service.upload_file(kuisioner_id, file, current_user["id"])


@router.get("/{kuisioner_id}/download", response_class=FileResponse)
async def download_kuisioner_file(
    kuisioner_id: str = Path(..., description="Kuisioner ID"),
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: KuisionerService = Depends(get_kuisioner_service)
):
    """Download kuisioner file."""
    return await service.download_file(kuisioner_id, download_type="download")


@router.get("/{kuisioner_id}/view", response_class=FileResponse)
async def view_kuisioner_file(
    kuisioner_id: str = Path(..., description="Kuisioner ID"),
    current_user: dict = Depends(require_evaluasi_read_access()),
    service: KuisionerService = Depends(get_kuisioner_service)
):
    """View/preview kuisioner file in browser."""
    return await service.download_file(kuisioner_id, download_type="view")